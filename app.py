import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

# --- 1. 구글 시트 연결 설정 ---
conn = st.connection("gsheets", type=GSheetsConnection)

AGE_GROUPS = ["7세 이하", "초등", "중등", "고등", "만 20세~24세", "만 25세 이상"]
PURPOSES = ["놀이", "휴식", "식사", "친목", "기타"]

# 로그인 및 페이지 세션 상태
if 'is_admin' not in st.session_state:
    if st.query_params.get("admin") == "true":
        st.session_state.is_admin = True
        st.session_state.page = 'admin'
    else:
        st.session_state.is_admin = False

if 'page' not in st.session_state:
    st.session_state.page = 'gender'
if 'temp_data' not in st.session_state:
    st.session_state.temp_data = {}

st.set_page_config(page_title="라미그라운드 방명록", layout="wide")

# --- 2. 디자인 (180x180 버튼) ---
st.markdown("""
    <style>
    div.stButton > button {
        width: 180px !important; height: 180px !important;
        font-size: 20px !important; font-weight: bold !important;
        border-radius: 20px !important; margin: 10px auto; display: block;
    }
    .center-text { text-align: center; padding: 20px; }
    .welcome-title { font-size: 42px; font-weight: 800; margin-bottom: 10px; }
    .sub-title { font-size: 24px; color: #555; margin-bottom: 40px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 유틸리티 ---
def get_kst_now():
    return datetime.utcnow() + timedelta(hours=9)

def create_excel_report(df):
    output = io.BytesIO()
    export_cols = ["일시", "연도", "월", "일자", "시간", "요일", "성별", "연령대", "이용목록"]
    # 엑셀 추출용 데이터 정리
    temp_df = df.copy()
    temp_df['일시'] = pd.to_datetime(temp_df['일시'])
    temp_df['연도'] = temp_df['일시'].dt.year
    temp_df['일자'] = temp_df['일시'].dt.day
    temp_df['시간'] = temp_df['일시'].dt.hour
    
    existing_cols = [col for col in export_cols if col in temp_df.columns]
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        temp_df[existing_cols].to_excel(writer, index=False, sheet_name='방문기록')
    return output.getvalue()

# --- 4. 메인 로직 ---

with st.sidebar:
    st.title("🛡️ 관리자 메뉴")
    if not st.session_state.is_admin:
        if st.checkbox("관리자 모드 접속"):
            admin_id = st.text_input("아이디")
            admin_pw = st.text_input("비밀번호", type="password")
            if st.button("로그인"):
                if admin_id == "jgyouth" and admin_pw == "youth2250!!":
                    st.session_state.is_admin = True
                    st.session_state.page = 'admin'
                    st.query_params["admin"] = "true"
                    st.rerun()
                else: st.error("정보가 틀립니다.")
    else:
        st.success("로그인 상태입니다.")
        if st.button("로그아웃"):
            st.session_state.is_admin = False
            st.session_state.page = 'gender'
            st.query_params.clear()
            st.rerun()

# [A] 관리자 페이지
if st.session_state.is_admin and st.session_state.page == 'admin':
    st.title("📊 관리자 대시보드 (Google Sheets)")
    df = conn.read(ttl=0)
    
    if not df.empty:
        df['일시'] = pd.to_datetime(df['일시'])
        df['연도'] = df['일시'].dt.year
        df['일자'] = df['일시'].dt.day
        df['시간'] = df['일시'].dt.hour

        with st.expander("🔍 상세 필터 설정", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                date_range = st.date_input("날짜 범위", [df['일시'].min().date(), df['일시'].max().date()])
            with col2:
                selected_gender = st.multiselect("성별", options=["남성", "여성"], default=["남성", "여성"])
            with col3:
                selected_ages = st.multiselect("연령대", options=AGE_GROUPS, default=AGE_GROUPS)

        mask = (df['일시'].dt.date >= date_range[0]) & (df['일시'].dt.date <= date_range[1]) & \
               (df['성별'].isin(selected_gender)) & (df['연령대'].isin(selected_ages))
        f_df = df[mask].copy()

        st.subheader("🗑️ 데이터 관리 및 삭제")
        # 편집용 데이터프레임 (인덱스 유지)
        display_df = f_df[["연도", "월", "일자", "요일", "시간", "성별", "연령대"]]
        edited_df = st.data_editor(display_df, num_rows="dynamic", use_container_width=True, key="admin_editor")
        
        if st.button("💾 변경사항 구글 시트에 저장"):
            try:
                # 1. 타입 변환 및 전처리
                edited_df['연도'] = pd.to_numeric(edited_df['연도']).fillna(0).astype(int)
                edited_df['월'] = pd.to_numeric(edited_df['월']).fillna(0).astype(int)
                edited_df['일자'] = pd.to_numeric(edited_df['일자']).fillna(0).astype(int)
                edited_df['시간'] = pd.to_numeric(edited_df['시간']).fillna(0).astype(int)
                
                # 2. '이용목록' 보존 (f_df에서 현재 편집된 행의 개수만큼 가져오거나 기본값 설정)
                # 삭제가 발생했을 수 있으므로 f_df와 매칭하지 않고 기본값 혹은 기존값 보존
                # (가장 안전한 방법: 편집된 데이터의 인덱스를 기준으로 원본에서 이용목록 가져오기)
                edited_df['이용목록'] = "기타"
                for idx in edited_df.index:
                    if idx in f_df.index:
                        edited_df.at[idx, '이용목록'] = f_df.at[idx, '이용목록']

                # 3. '일시' 컬럼 재생성 (에러 발생 구간 수정)
                def format_date(row):
                    return f"{row['연도']}-{row['월']:02d}-{row['일자']:02d} {row['시간']:02d}:00:00"
                
                edited_df['일시'] = edited_df.apply(format_date, axis=1)
                
                # 4. 필터링되지 않은 데이터와 합쳐서 최종본 생성
                final_save_df = pd.concat([df[~mask], edited_df], ignore_index=True)
                save_cols = ["일시", "요일", "월", "성별", "연령대", "이용목록"]
                
                # 5. 구글 시트 업데이트
                conn.update(data=final_save_df[save_cols])
                st.success("구글 시트가 성공적으로 업데이트되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"저장 중 오류가 발생했습니다: {e}")

        st.download_button("📥 필터링 데이터 엑셀 추출", data=create_excel_report(f_df), file_name="라미그라운드_통계.xlsx")

        st.divider()
        st.subheader("📈 시각화 현황 분석")
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.pie(f_df, names='성별', title='성별 비중', hole=0.4), use_container_width=True)
        with c2: st.plotly_chart(px.pie(f_df, names='이용목록', title='이용 목적 비중', hole=0.4), use_container_width=True)
        
        c3, c4 = st.columns(2)
        with c3:
            age_chart = f_df['연령대'].value_counts().reindex(AGE_GROUPS).reset_index()
            st.plotly_chart(px.bar(age_chart, x='연령대', y='count', title='연령대별'), use_container_width=True)
        with c4:
            hour_chart = f_df['시간'].value_counts().sort_index().reset_index()
            st.plotly_chart(px.line(hour_chart, x='시간', y='count', title='시간대별', markers=True), use_container_width=True)
    else: st.info("시트에 데이터가 없습니다.")

# [B] 사용자 페이지 (성별)
elif st.session_state.page == 'gender':
    st.markdown("<div class='center-text'><div class='welcome-title'>라미그라운드 방문을 환영합니다! 😊</div><div class='sub-title'>성별을 선택해주세요.</div></div>", unsafe_allow_html=True)
    _, c2, c3, _ = st.columns([1, 1, 1, 1])
    with c2: 
        if st.button("남성"): st.session_state.temp_data['gender'] = "남성"; st.session_state.page = 'age'; st.rerun()
    with c3: 
        if st.button("여성"): st.session_state.temp_data['gender'] = "여성"; st.session_state.page = 'age'; st.rerun()

# [C] 사용자 페이지 (연령대)
elif st.session_state.page == 'age':
    st.markdown("<div class='center-text'><div class='sub-title'>연령대를 선택해주세요.</div></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, age in enumerate(AGE_GROUPS):
        with cols[i % 3]:
            if st.button(age): st.session_state.temp_data['age'] = age; st.session_state.page = 'purpose'; st.rerun()

# [D] 사용자 페이지 (이용 목적)
elif st.session_state.page == 'purpose':
    st.markdown("<div class='center-text'><div class='sub-title'>오늘 이용 목적은 무엇인가요?</div></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, purp in enumerate(PURPOSES):
        with cols[i % 3]:
            if st.button(purp):
                now = get_kst_now()
                new_row = pd.DataFrame([{
                    "일시": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "요일": now.strftime("%A"),
                    "월": now.month,
                    "성별": st.session_state.temp_data['gender'],
                    "연령대": st.session_state.temp_data['age'],
                    "이용목록": purp
                }])
                existing_df = conn.read(ttl=0)
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.session_state.page = 'complete'; st.rerun()

# [E] 사용자 페이지 (완료)
elif st.session_state.page == 'complete':
    st.balloons()
    st.markdown("<div class='center-text' style='margin-top:100px;'><div class='welcome-title'>✅ 접수 완료!</div><div class='sub-title'>감사합니다. 즐거운 시간 되세요!</div></div>", unsafe_allow_html=True)
    import time
    time.sleep(3)
    st.session_state.page = 'gender'; st.rerun()