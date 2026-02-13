import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import io
import time

# --- 1. 기본 설정 및 데이터 로드 ---
DB_FILE = "visitor_log.csv"
AGE_GROUPS = ["7세 이하", "초등", "중등", "고등", "만 20세~24세", "만 25세 이상"]
PURPOSES = ["놀이", "휴식", "식사", "친목", "기타"]

if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["일시", "요일", "월", "성별", "연령대", "이용목록"])
    df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

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

# --- 2. 디자인 (CSS: 버튼 사이즈 및 중앙 정렬 강제) ---
st.markdown("""
    <style>
    /* 가로 간격 고정 */
    [data-testid="stHorizontalBlock"] { gap: 20px !important; }

    /* 메인 버튼 (180x180) */
    div[data-testid="stButton"] button:not(.back-btn) {
        width: 180px !important;
        height: 180px !important;
        min-width: 180px !important;
        min-height: 180px !important;
        flex-shrink: 0 !important;
        font-size: 24px !important;
        font-weight: 800 !important;
        border-radius: 25px !important;
        box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 auto !important;
    }

    /* 뒤로 가기 버튼 (180x60, 노란색) */
    .yellow-btn-area div[data-testid="stButton"] button {
        background-color: #FFD700 !important;
        color: #000 !important;
        width: 180px !important;
        height: 60px !important;
        min-width: 180px !important;
        min-height: 60px !important;
        flex-shrink: 0 !important;
        font-size: 20px !important;
        font-weight: 900 !important;
        border-radius: 12px !important;
        border: none !important;
        margin: 100px auto 0 !important;
    }

    .center-text { text-align: center; padding: 20px; }
    .welcome-title { font-size: 48px; font-weight: 900; margin-bottom: 10px; }
    .sub-title { font-size: 26px; color: #444; margin-bottom: 50px; font-weight: 600; }
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
    st.title("📊 데이터 관리 및 통계 분석")
    df = pd.read_csv(DB_FILE)
    df['일시'] = pd.to_datetime(df['일시'])
    
    if not df.empty:
        # 필터링 섹션
        with st.expander("🔍 상세 필터링 설정", expanded=True):
            f1, f2 = st.columns(2)
            with f1: date_range = st.date_input("날짜 범위", [df['일시'].min().date(), df['일시'].max().date()])
            with f2: selected_gender = st.multiselect("성별", options=["남성", "여성"], default=["남성", "여성"])
            f3, f4 = st.columns(2)
            with f3: selected_ages = st.multiselect("연령대", options=AGE_GROUPS, default=AGE_GROUPS)
            with f4: selected_purposes = st.multiselect("이용 목적", options=PURPOSES, default=PURPOSES)

        mask = (df['일시'].dt.date >= date_range[0]) & (df['일시'].dt.date <= date_range[1]) & \
               (df['성별'].isin(selected_gender)) & (df['연령대'].isin(selected_ages)) & \
               (df['이용목록'].isin(selected_purposes))
        f_df = df[mask].copy()

        st.subheader("🗑️ 데이터 편집 및 삭제")
        edited_df = st.data_editor(f_df, num_rows="dynamic", use_container_width=True, key="data_editor")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 변경사항 최종 저장", use_container_width=True):
                try:
                    final_df = pd.concat([df[~mask], edited_df], ignore_index=True)
                    final_df[["일시", "요일", "월", "성별", "연령대", "이용목록"]].to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                    st.success("저장 완료!"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"오류: {e}")
        with c2:
            st.download_button("📥 필터링 데이터 엑셀 추출", data=create_excel_report(f_df), file_name="현황.xlsx", use_container_width=True)

        st.divider()
        if not f_df.empty:
            # 일자별 그래프 추가 (수정 사항 2)
            st.subheader("📅 일자별 방문 추이")
            daily_counts = f_df['일시'].dt.date.value_counts().sort_index().reset_index()
            daily_counts.columns = ['날짜', '방문자 수']
            st.plotly_chart(px.line(daily_counts, x='날짜', y='방문자 수', markers=True, title="일자별 방문객 흐름"), use_container_width=True)

            row1_1, row1_2 = st.columns(2)
            with row1_1: st.plotly_chart(px.pie(f_df, names='성별', title='성별 비중', hole=0.4), use_container_width=True)
            with row1_2: st.plotly_chart(px.pie(f_df, names='이용목록', title='이용 목적 비중', hole=0.4), use_container_width=True)
    else: st.info("데이터가 없습니다.")

# [B] 사용자 페이지: 성별 (중앙 정렬 수정 사항 1)
elif st.session_state.page == 'gender':
    st.markdown("<div class='center-text'><div class='welcome-title'>라미그라운드 방문을 환영합니다! 😊</div><div class='sub-title'>성별을 선택해주세요.</div></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 2, 1]) # 가로 중간 배치
    with center_col:
        c1, c2 = st.columns(2)
        if c1.button("남성"): st.session_state.temp_data['gender'] = "남성"; st.session_state.page = 'age'; st.rerun()
        if c2.button("여성"): st.session_state.temp_data['gender'] = "여성"; st.session_state.page = 'age'; st.rerun()

# [C] 사용자 페이지: 연령대 (중앙 정렬 수정 사항 1)
elif st.session_state.page == 'age':
    st.markdown("<div class='center-text'><div class='sub-title'>연령대를 선택해주세요.</div></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 3, 1]) # 가로 중간 배치
    with center_col:
        c1, c2, c3 = st.columns(3)
        for i, age in enumerate(AGE_GROUPS):
            if [c1, c2, c3][i % 3].button(age):
                st.session_state.temp_data['age'] = age; st.session_state.page = 'purpose'; st.rerun()
    
    _, back_col, _ = st.columns([1, 1, 1])
    with back_col:
        st.markdown("<div class='yellow-btn-area'>", unsafe_allow_html=True)
        if st.button("뒤로 가기", key="back_to_gender"): st.session_state.page = 'gender'; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# [D] 사용자 페이지: 이용 목적 (중앙 정렬 수정 사항 1)
elif st.session_state.page == 'purpose':
    st.markdown("<div class='center-text'><div class='sub-title'>오늘 이용 목적은 무엇인가요?</div></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 3, 1]) # 가로 중간 배치
    with center_col:
        c1, c2, c3 = st.columns(3)
        for i, purp in enumerate(PURPOSES):
            if [c1, c2, c3][i % 3].button(purp):
                now = get_kst_now()
                new_row = {"일시": now.strftime("%Y-%m-%d %H:%M:%S"), "요일": now.strftime("%A"), "월": now.month, "성별": st.session_state.temp_data['gender'], "연령대": st.session_state.temp_data['age'], "이용목록": purp}
                df = pd.read_csv(DB_FILE)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.session_state.page = 'complete'; st.rerun()

    _, back_col, _ = st.columns([1, 1, 1])
    with back_col:
        st.markdown("<div class='yellow-btn-area'>", unsafe_allow_html=True)
        if st.button("뒤로 가기", key="back_to_age"): st.session_state.page = 'age'; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# [E] 사용자 페이지: 완료
elif st.session_state.page == 'complete':
    st.balloons()
    st.markdown("<div class='center-text' style='margin-top:100px;'><div class='welcome-title'>✅ 접수 완료!</div><div class='sub-title'>감사합니다. 즐거운 시간 되세요!</div></div>", unsafe_allow_html=True)
    time.sleep(2.0)
    st.session_state.page = 'gender'; st.rerun()