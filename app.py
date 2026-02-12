import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import io

# --- 1. 기본 설정 및 데이터 로드 ---
DB_FILE = "visitor_log.csv"
AGE_GROUPS = ["7세 이하", "초등", "중등", "고등", "만 20세~24세", "만 25세 이상"]
PURPOSES = ["놀이", "휴식", "식사", "친목", "기타"]

# 데이터 파일 초기화 (이용장소 삭제)
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["일시", "요일", "월", "성별", "연령대", "이용목적"])
    df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# 세션 상태 초기화
if 'page' not in st.session_state:
    st.session_state.page = 'gender'
if 'temp_data' not in st.session_state:
    st.session_state.temp_data = {}

st.set_page_config(page_title="중구청소년센터 방명록", layout="wide")

# --- 2. 디자인 개선 (180x180 정사각 버튼 및 중앙 정렬) ---
st.markdown("""
    <style>
    /* 전체 배경색 및 폰트 */
    .main { background-color: #ffffff; }
    
    /* 버튼 스타일: 가로 180px, 세로 180px 고정 */
    div.stButton > button {
        width: 180px !important;
        height: 180px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 20px !important;
        background-color: #f8f9fa !important;
        color: #333333 !important;
        border: 2px solid #e9ecef !important;
        transition: all 0.3s ease;
        display: block;
        margin: 10px auto; /* 버튼 중앙 정렬 */
    }
    
    /* 버튼 호버 효과 */
    div.stButton > button:hover {
        border-color: #007bff !important;
        color: #007bff !important;
        background-color: #e7f1ff !important;
    }

    /* 제목 및 안내 문구 중앙 정렬 */
    .center-text {
        text-align: center;
        padding: 20px;
        color: #2c3e50;
    }
    .welcome-title { font-size: 42px; font-weight: 800; margin-bottom: 10px; }
    .sub-title { font-size: 24px; color: #555; margin-bottom: 40px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 엑셀 리포트 생성 함수 ---
def create_excel_report(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='방문기록')
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

# [A] 관리자 페이지 (장소 관련 내용 삭제)
if st.session_state.page == 'admin':
    st.title("📊 상세 이용 현황 분석")
    df = pd.read_csv(DB_FILE)
    df['일시'] = pd.to_datetime(df['일시'])

    if not df.empty:
        with st.expander("🔍 상세 필터 설정", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                date_range = st.date_input("날짜 범위", [df['일시'].min(), df['일시'].max()])
                selected_gender = st.multiselect("성별", options=["남성", "여성"], default=["남성", "여성"])
            with col2:
                selected_ages = st.multiselect("연령대", options=AGE_GROUPS, default=AGE_GROUPS)
                selected_purp = st.multiselect("이용목적", options=PURPOSES, default=PURPOSES)

        mask = (df['일시'].dt.date >= date_range[0]) & (df['일시'].dt.date <= date_range[1]) & \
               (df['성별'].isin(selected_gender)) & (df['연령대'].isin(selected_ages)) & \
               (df['이용목적'].isin(selected_purp))
        f_df = df[mask]

        st.subheader("🗑️ 데이터 관리 및 삭제")
        edited_df = st.data_editor(f_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 변경사항 저장"):
            final_df = pd.concat([df[~mask], edited_df], ignore_index=True)
            final_df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
            st.success("데이터가 업데이트되었습니다.")
            st.rerun()

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("📍 이용 목적별 분포")
            st.plotly_chart(px.pie(f_df, names='이용목적', hole=0.3), use_container_width=True)
        with col_b:
            st.subheader("👥 연령대별 방문 분포")
            st.plotly_chart(px.bar(f_df['연령대'].value_counts().reset_index(), x='연령대', y='count'), use_container_width=True)

        st.download_button("📥 필터링 데이터 다운로드", data=create_excel_report(f_df), file_name="중구청소년센터_통계.xlsx")
    else:
        st.info("데이터가 없습니다.")

# [B] 사용자 페이지 1: 성별 선택 (문구 수정)
elif st.session_state.page == 'gender':
    st.markdown("<div class='center-text'><div class='welcome-title'>중구청소년센터 방문을 환영합니다! 😊</div><div class='sub-title'>성별을 선택해주세요.</div></div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col2:
        if st.button("남성"):
            st.session_state.temp_data['gender'] = "남성"
            st.session_state.page = 'age'
            st.rerun()
    with col3:
        if st.button("여성"):
            st.session_state.temp_data['gender'] = "여성"
            st.session_state.page = 'age'
            st.rerun()

# [C] 사용자 페이지 2: 연령대 선택
elif st.session_state.page == 'age':
    st.markdown("<div class='center-text'><div class='sub-title'>연령대를 선택해주세요.</div></div>", unsafe_allow_html=True)
    # 3열 배치를 통해 180px 버튼들이 예쁘게 배열되도록 조정
    cols = st.columns(3)
    for i, age in enumerate(AGE_GROUPS):
        with cols[i % 3]:
            if st.button(age):
                st.session_state.temp_data['age'] = age
                st.session_state.page = 'purpose'
                st.rerun()

# [D] 사용자 페이지 3: 이용 목적 선택 (여기서 데이터 저장)
elif st.session_state.page == 'purpose':
    st.markdown("<div class='center-text'><div class='sub-title'>오늘 이용 목적은 무엇인가요?</div></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, purp in enumerate(PURPOSES):
        with cols[i % 3]:
            if st.button(purp):
                now = datetime.now()
                new_row = {
                    "일시": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "요일": now.strftime("%A"),
                    "월": now.month,
                    "성별": st.session_state.temp_data['gender'],
                    "연령대": st.session_state.temp_data['age'],
                    "이용목적": purp
                }
                df = pd.read_csv(DB_FILE)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.session_state.page = 'complete'
                st.rerun()

# [E] 사용자 페이지 4: 완료
elif st.session_state.page == 'complete':
    st.balloons()
    st.markdown("<div class='center-text' style='margin-top:100px;'><div class='welcome-title'>✅ 접수 완료!</div><div class='sub-title'>감사합니다. 즐거운 시간 되세요!</div></div>", unsafe_allow_html=True)
    import time
    time.sleep(3)
    st.session_state.page = 'gender'
    st.rerun()