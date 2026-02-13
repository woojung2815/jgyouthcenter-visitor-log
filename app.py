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

if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["일시", "요일", "월", "성별", "연령대", "이용목록"])
    df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# 로그인 상태 유지 로직
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

# --- 2. 디자인 (CSS) ---
st.markdown("""
    <style>
    /* 전체 레이아웃 가로 간격 20px 고정 */
    [data-testid="stHorizontalBlock"] {
        gap: 20px !important;
    }

    /* 메인 선택 버튼 (180x180) */
    div.stButton > button:not(.back-btn) {
        width: 180px !important; 
        height: 180px !important;
        font-size: 22px !important; 
        font-weight: bold !important;
        border-radius: 25px !important; 
        margin: 0 auto; 
        display: block;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* 뒤로 가기 버튼 전용 스타일 (180x60) */
    .yellow-btn button {
        background-color: #FFD700 !important;
        color: #333 !important;
        height: 60px !important;
        width: 180px !important;
        border: none !important;
        font-size: 18px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
    }
    
    /* 섹션 간 세로 간격 조절 (100px) */
    .back-spacer {
        margin-top: 100px;
    }
    
    /* 텍스트 중앙 정렬 */
    .center-text { text-align: center; padding: 20px; }
    .welcome-title { font-size: 46px; font-weight: 800; margin-bottom: 10px; color: #1E1E1E; }
    .sub-title { font-size: 26px; color: #666; margin-bottom: 50px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 유틸리티 함수 ---
def get_kst_now():
    return datetime.utcnow() + timedelta(hours=9)

def create_excel_report(df):
    output = io.BytesIO()
    export_cols = ["일시", "연도", "월", "일자", "시간", "요일", "성별", "연령대", "이용목록"]
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
        st.success("로그인 성공")
        if st.button("로그아웃"):
            st.session_state.is_admin = False
            st.session_state.page = 'gender'
            st.query_params.clear()
            st.rerun()

# [A] 관리자 페이지
if st.session_state.is_admin and st.session_state.page == 'admin':
    st.title("📊 관리자 대시보드")
    df = pd.read_csv(DB_FILE)
    df['일시'] = pd.to_datetime(df['