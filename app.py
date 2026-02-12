import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import io

# --- 1. 기본 설정 및 데이터 로드 ---
DB_FILE = "visitor_log.csv"
AGE_GROUPS = ["7세 이하", "초등", "중등", "고등", "만 20세~24세", "만 25세 이상"]
PURPOSES = ["놀이", "휴식", "식사", "친목", "기타"]

# 데이터 파일 초기화
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["일시", "요일", "월", "성별", "연령대", "이용목록"])
    df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# 새로고침 시 로그인 상태 복구 로직
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

# --- 2. 디자인 (180x180 버튼 및 중앙 정렬) ---
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

# --- 3. 유틸리티 함수 ---
def get_kst_now():
    return datetime.utcnow() + timedelta(hours=9)

# [수정] 요청하신 순서대로 엑셀 컬럼을 정렬하여 생성
def create_excel_report(df):
    output = io.BytesIO()
    # 엑셀용 컬럼 순서 정의
    export_cols = ["일시", "연도", "월", "일자", "시간", "요일", "성별", "연령대", "이용목록"]
    # 데이터프레임에 해당 컬럼들이 있는지 확인 후 순서 배치
    existing_cols = [col for col in export_cols if col in df.columns]
    export_df = df[existing_cols]
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        export_df.to_excel(writer, index=False, sheet_name='방문기록')
    return output.getvalue()

# --- 4. 메인 로직 ---

# [사이드바: 관리자 로그인 및 상태 유지]
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
                else:
                    st.error("정보가 틀립니다.")
    else:
        st.success("로그인 상태입니다.")
        if st.button("로그아웃"):
            st.session_state.is_admin = False
            st.session_state.page = 'gender'
            st.query_params.clear()
            st.rerun()

# [A] 관리자 페이지
if st.session_state.is_admin and st.session_state.page == 'admin':
    st.title("📊 관리자 대시보드")
    df = pd.read_csv(DB_FILE)
    df['일시'] = pd.to_datetime(df['일시'])
    
    # 시간 데이터 상세 분리
    df['연도'] = df['일시'].dt.year
    df['일자'] = df['일시'].dt.day
    df['시간'] = df['일시'].dt.hour

    if not df.empty:
        # 상단 필터
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
        f_df = df[mask]

        # 데이터 관리 및 삭제 (시각화 위)
        st.subheader("🗑️ 데이터 관리 및 삭제")
        display_df = f_df[["연도", "월", "일자", "요일", "시간", "성별", "연령대"]]
        
        edited_df = st.data_editor(display_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 변경사항 저장"):
            edited_df['이용목록'] = f_df['이용목록'].values[:len(edited_df)]
            edited_df['이용목록'] = edited_df['이용목록'].fillna('기타')
            edited_df['일시'] = edited_df.apply(lambda row: f"{row['연도']}-{row['월']:02d}-{row['일자']:02d} {row['시간']:02d}:00:00", axis=1)
            
            final_save_df = pd.concat([df[~mask], edited_df], ignore_index=True)
            save_cols = ["일시", "요일", "월", "성별", "연령대", "이용목록"]
            final_save_df[save_cols].to_csv(DB_FILE, index=False, encoding='utf-8-sig')
            st.success("데이터가 업데이트되었습니다.")
            st.rerun()

        # [수정] 엑셀 추출 버튼
        st.download_button(
            "📥 필터링 데이터 엑셀 추출", 
            data=create_excel_report(f_df), 
            file_name=f"라미그라운드_통계_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )

        # 시각화 분석 (하단)
        st.divider()
        st.subheader("📈 시각화 현황 분석")
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            st.plotly_chart(px.pie(f_df, names='성별', title='성별 이용 비중', hole=0.4), use_container_width=True)
        with row1_col2:
            st.plotly_chart(px.pie(f_df, names='이용목록', title='이용 목적별 비중', hole=0.4), use_container_width=True)

        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            age_counts = f_df['연령대'].value_counts().reindex(AGE_GROUPS).fillna(0).reset_index()
            st.plotly_chart(px.bar(age_counts, x='연령대', y='count', title='연령대별 방문자 수'), use_container_width=True)
        with row2_col2:
            hour_counts = f_df['시간'].value_counts().sort_index().reset_index()
            st.plotly_chart(px.line(hour_counts, x='시간', y='count', title='시간대별 방문 패턴', markers=True), use_container_width=True)
    else:
        st.info("데이터가 없습니다.")

# [B] 사용자 페이지 1: 성별 선택
elif st.session_state.page == 'gender':
    st.markdown("<div class='center-text'><div class='welcome-title'>라미그라운드 방문을 환영합니다! 😊</div><div class='sub-title'>성별을 선택해주세요.</div></div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col2:
        if st.button("남성"):
            st.session_state.temp_data['gender'] = "남성"; st.session_state.page = 'age'; st.rerun()
    with col3:
        if st.button("여성"):
            st.session_state.temp_data['gender'] = "여성"; st.session_state.page = 'age'; st.rerun()

# [C] 사용자 페이지 2: 연령대 선택
elif st.session_state.page == 'age':
    st.markdown("<div class='center-text'><div class='sub-title'>연령대를 선택해주세요.</div></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, age in enumerate(AGE_GROUPS):
        with cols[i % 3]:
            if st.button(age):
                st.session_state.temp_data['age'] = age; st.session_state.page = 'purpose'; st.rerun()

# [D] 사용자 페이지 3: 이용 목적 선택
elif st.session_state.page == 'purpose':
    st.markdown("<div class='center-text'><div class='sub-title'>오늘 이용 목적은 무엇인가요?</div></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, purp in enumerate(PURPOSES):
        with cols[i % 3]:
            if st.button(purp):
                now = get_kst_now()
                new_row = {
                    "일시": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "요일": now.strftime("%A"),
                    "월": now.month,
                    "성별": st.session_state.temp_data['gender'],
                    "연령대": st.session_state.temp_data['age'],
                    "이용목록": purp 
                }
                df = pd.read_csv(DB_FILE)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.session_state.page = 'complete'; st.rerun()

# [E] 사용자 페이지 4: 완료
elif st.session_state.page == 'complete':
    st.balloons()
    st.markdown("<div class='center-text' style='margin-top:100px;'><div class='welcome-title'>✅ 접수 완료!</div><div class='sub-title'>감사합니다. 즐거운 시간 되세요!</div></div>", unsafe_allow_html=True)
    import time
    time.sleep(3)
    st.session_state.page = 'gender'; st.rerun()