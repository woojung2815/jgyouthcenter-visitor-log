import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import io

# --- 1. 기본 설정 및 데이터 로드 ---
DB_FILE = "visitor_log.csv"
LOCATIONS = ["라미라운지", "라미그라운드", "라미의숲", "라미스튜디오", "라미의방", "복합문화공간", "강의실", "체육관"]
AGE_GROUPS = ["7세 이하", "초등", "중등", "고등", "만 20세~24세", "만 25세 이상"]
PURPOSES = ["놀이", "휴식", "식사", "친목", "기타"]

# 데이터 파일 및 컬럼 초기화 (이용목적 추가)
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["일시", "요일", "월", "성별", "연령대", "이용목적", "이용장소"])
    df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# 세션 상태 초기화
if 'page' not in st.session_state:
    st.session_state.page = 'gender'
if 'temp_data' not in st.session_state:
    st.session_state.temp_data = {}

st.set_page_config(page_title="라미 센터 방명록", layout="wide")

# --- 2. 디자인 개선 (CSS 삽입) ---
st.markdown("""
    <style>
    /* 버튼 크기 및 모양 (가로세로 비율 조정) */
    div.stButton > button {
        width: 100%;
        height: 180px !important;
        font-size: 24px !important;
        font-weight: bold !important;
        border-radius: 15px !important;
        margin-bottom: 10px;
        border: 2px solid #f0f2f6;
    }
    /* 중앙 정렬 안내 문구 */
    .center-text {
        text-align: center;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 엑셀 리포트 생성 함수 ---
def create_excel_report(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='방문기록')
        workbook = writer.book
        worksheet = writer.sheets['방문기록']
        worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
    return output.getvalue()

# --- 4. 메인 로직 ---

# [사이드바: 관리자 로그인]
with st.sidebar:
    st.title("🛡️ 관리자 메뉴")
    if st.checkbox("관리자 모드 접속"):
        admin_id = st.text_input("아이디")
        admin_pw = st.text_input("비밀번호", type="password")
        if admin_id == "jgyouth" and admin_pw == "youth2250!!":
            st.success("인증 성공")
            st.session_state.page = 'admin'
        else:
            if admin_id or admin_pw: st.error("정보가 틀립니다.")
    else:
        if st.session_state.page == 'admin': st.session_state.page = 'gender'

# [A] 관리자 페이지
if st.session_state.page == 'admin':
    st.title("📊 상세 이용 현황 분석")
    df = pd.read_csv(DB_FILE)
    df['일시'] = pd.to_datetime(df['일시'])

    if not df.empty:
        # --- 필터 섹션 ---
        with st.expander("🔍 상세 필터 설정 (여기를 클릭하세요)", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                date_range = st.date_input("날짜 범위", [df['일시'].min(), df['일시'].max()])
                selected_gender = st.multiselect("성별", options=["남성", "여성"], default=["남성", "여성"])
            with col2:
                selected_ages = st.multiselect("연령대", options=AGE_GROUPS, default=AGE_GROUPS)
                selected_days = st.multiselect("요일", options=df['요일'].unique(), default=df['요일'].unique())
            with col3:
                selected_locs = st.multiselect("장소", options=LOCATIONS, default=LOCATIONS)
                selected_month = st.multiselect("월(Month)", options=sorted(df['일시'].dt.month.unique()), default=sorted(df['일시'].dt.month.unique()))

        # 필터 적용
        mask = (df['일시'].dt.date >= date_range[0]) & (df['일시'].dt.date <= date_range[1]) & \
               (df['성별'].isin(selected_gender)) & (df['연령대'].isin(selected_ages)) & \
               (df['요일'].isin(selected_days)) & (df['이용장소'].isin(selected_locs)) & \
               (df['일시'].dt.month.isin(selected_month))
        f_df = df[mask]

        # 데이터 삭제 기능
        st.subheader("🗑️ 데이터 관리 (삭제 가능)")
        st.write("삭제를 원하시면 행을 선택한 뒤 [Delete] 키를 누르거나, 수정 후 저장하세요.")
        edited_df = st.data_editor(f_df, num_rows="dynamic", use_container_width=True, key="data_editor")
        
        if st.button("💾 변경사항(삭제 등) 저장하기"):
            # 필터링되지 않은 데이터와 수정한 데이터를 합쳐서 저장
            other_data = df[~mask]
            final_df = pd.concat([other_data, edited_df], ignore_index=True)
            final_df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
            st.success("데이터가 업데이트되었습니다!")
            st.rerun()

        st.divider()

        # 시각화 그래프
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📍 이용 목적별 분포")
            st.plotly_chart(px.pie(f_df, names='이용목적', hole=0.3), use_container_width=True)
        with c2:
            st.subheader("📅 연령대별 방문 현황")
            st.plotly_chart(px.bar(f_df['연령대'].value_counts().reset_index(), x='연령대', y='count', color='연령대'), use_container_width=True)

        st.download_button("📥 필터링된 데이터 엑셀 다운로드", data=create_excel_report(f_df), file_name="라미센터_맞춤추출.xlsx")
    else:
        st.info("데이터가 없습니다.")

# [B] 사용자 페이지 (성별)
elif st.session_state.page == 'gender':
    st.markdown("<h1 class='center-text'>성별을 선택해 주세요</h1>", unsafe_allow_html=True)
    _, m, _ = st.columns([1, 2, 1])
    with m:
        c1, c2 = st.columns(2)
        if c1.button("남성"): st.session_state.temp_data['gender'] = "남성"; st.session_state.page = 'age'; st.rerun()
        if c2.button("여성"): st.session_state.temp_data['gender'] = "여성"; st.session_state.page = 'age'; st.rerun()

# [C] 사용자 페이지 (연령대)
elif st.session_state.page == 'age':
    st.markdown("<h1 class='center-text'>연령대를 선택해 주세요</h1>", unsafe_allow_html=True)
    _, m, _ = st.columns([1, 2, 1])
    with m:
        cols = st.columns(2)
        for i, age in enumerate(AGE_GROUPS):
            if cols[i%2].button(age):
                st.session_state.temp_data['age'] = age; st.session_state.page = 'purpose'; st.rerun()

# [D] 사용자 페이지 (이용 목적 - 신설)
elif st.session_state.page == 'purpose':
    st.markdown("<h1 class='center-text'>오늘 이용 목적은 무엇인가요?</h1>", unsafe_allow_html=True)
    _, m, _ = st.columns([1, 2, 1])
    with m:
        cols = st.columns(2)
        for i, purp in enumerate(PURPOSES):
            if cols[i%2].button(purp):
                st.session_state.temp_data['purpose'] = purp; st.session_state.page = 'location'; st.rerun()

# [E] 사용자 페이지 (장소)
elif st.session_state.page == 'location':
    st.markdown("<h1 class='center-text'>이용하실 장소를 선택해 주세요</h1>", unsafe_allow_html=True)
    _, m, _ = st.columns([1, 2, 1])
    with m:
        cols = st.columns(2)
        for i, loc in enumerate(LOCATIONS):
            if cols[i%2].button(loc):
                now = datetime.now()
                new_row = {
                    "일시": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "요일": now.strftime("%A"),
                    "월": now.month,
                    "성별": st.session_state.temp_data['gender'],
                    "연령대": st.session_state.temp_data['age'],
                    "이용목적": st.session_state.temp_data['purpose'],
                    "이용장소": loc
                }
                df = pd.read_csv(DB_FILE)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.session_state.page = 'complete'; st.rerun()

# [F] 사용자 페이지 (완료)
elif st.session_state.page == 'complete':
    st.balloons()
    st.markdown("<h1 style='text-align:center;'>✅ 접수 완료!</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align:center;'>즐거운 {st.session_state.temp_data['purpose']} 시간 되세요!</h3>", unsafe_allow_html=True)
    import time
    time.sleep(3)
    st.session_state.page = 'gender'; st.rerun()