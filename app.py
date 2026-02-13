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

# 관리자 로그인 상태 유지
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
    [data-testid="stHorizontalBlock"] { gap: 20px !important; }
    div.stButton > button:not(.back-btn) {
        width: 180px !important; height: 180px !important;
        font-size: 22px !important; font-weight: bold !important;
        border-radius: 25px !important; margin: 0 auto; display: block;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .yellow-btn button {
        background-color: #FFD700 !important; color: #333 !important;
        height: 60px !important; width: 180px !important;
        border: none !important; font-size: 18px !important;
        border-radius: 12px !important; font-weight: bold !important;
    }
    .back-spacer { margin-top: 100px; }
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
    st.title("📊 데이터 통합 관리 대시보드")
    df = pd.read_csv(DB_FILE)
    df['일시'] = pd.to_datetime(df['일시'])
    
    if not df.empty:
        # 시간 데이터 분리
        df['연도'] = df['일시'].dt.year
        df['일자'] = df['일시'].dt.day
        df['시간'] = df['일시'].dt.hour
        
        # 🔍 필터 섹션
        with st.expander("🔍 상세 필터링 (필터 결과에 따라 시각화와 삭제 테이블이 변경됩니다)", expanded=True):
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                date_range = st.date_input("날짜 범위", [df['일시'].min().date(), df['일시'].max().date()])
            with f_col2:
                selected_gender = st.multiselect("성별", options=["남성", "여성"], default=["남성", "여성"])
            with f_col3:
                selected_ages = st.multiselect("연령대", options=AGE_GROUPS, default=AGE_GROUPS)

        # 필터링 적용
        mask = (df['일시'].dt.date >= date_range[0]) & (df['일시'].dt.date <= date_range[1]) & \
               (df['성별'].isin(selected_gender)) & (df['연령대'].isin(selected_ages))
        f_df = df[mask].copy()

        # 🗑️ 데이터 관리 및 삭제 섹션
        st.subheader("🗑️ 데이터 편집 및 삭제")
        st.info("아래 표에서 행을 선택하고 키보드의 'Delete' 키를 누르거나, 우측의 쓰레기통 아이콘을 클릭하여 삭제할 수 있습니다.")
        
        # 삭제 및 수정을 위한 데이터 에디터
        # '일시'는 원본 보존을 위해 제외하고 표시하거나 편집 가능하게 설정
        edited_df = st.data_editor(
            f_df, 
            num_rows="dynamic", # 행 삭제 및 추가 가능
            use_container_width=True,
            column_order=["일시", "요일", "성별", "연령대", "이용목록"],
            key="data_editor"
        )

        if st.button("💾 변경사항 최종 저장"):
            # 필터링되지 않은 데이터 + 필터링 후 수정된 데이터를 합침
            final_df = pd.concat([df[~mask], edited_df], ignore_index=True)
            # 불필요한 보조 컬럼 제거 후 저장
            save_cols = ["일시", "요일", "월", "성별", "연령대", "이용목록"]
            final_df[save_cols].to_csv(DB_FILE, index=False, encoding='utf-8-sig')
            st.success("변경사항이 성공적으로 파일에 저장되었습니다!")
            time.sleep(1)
            st.rerun()

        st.divider()

        # 📈 시각화 분석
        if not f_df.empty:
            st.subheader("📈 필터링 데이터 분석 결과")
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.pie(f_df, names='성별', title='성별 비중', hole=0.4), use_container_width=True)
            with c2:
                st.plotly_chart(px.pie(f_df, names='이용목록', title='이용 목적 비중', hole=0.4), use_container_width=True)
            
            c3, c4 = st.columns(2)
            with c3:
                age_order = f_df['연령대'].value_counts().reindex(AGE_GROUPS).reset_index()
                st.plotly_chart(px.bar(age_order, x='연령대', y='count', title='연령대별 방문'), use_container_width=True)
            with c4:
                hour_trend = f_df['시간'].value_counts().sort_index().reset_index()
                st.plotly_chart(px.line(hour_trend, x='시간', y='count', title='시간대별 방문 패턴', markers=True), use_container_width=True)
            
            st.download_button("📥 현재 필터링된 데이터 엑셀로 받기", data=create_excel_report(f_df), file_name="라미그라운드_데이터.xlsx")
    else:
        st.info("표시할 데이터가 없습니다.")

# [B] 사용자 페이지: 성별
elif st.session_state.page == 'gender':
    st.markdown("<div class='center-text'><div class='welcome-title'>라미그라운드 방문을 환영합니다! 😊</div><div class='sub-title'>성별을 선택해주세요.</div></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 4, 1])
    with center_col:
        c1, c2 = st.columns(2)
        if c1.button("남성"): st.session_state.temp_data['gender'] = "남성"; st.session_state.page = 'age'; st.rerun()
        if c2.button("여성"): st.session_state.temp_data['gender'] = "여성"; st.session_state.page = 'age'; st.rerun()

# [C] 사용자 페이지: 연령대
elif st.session_state.page == 'age':
    st.markdown("<div class='center-text'><div class='sub-title'>연령대를 선택해주세요.</div></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 6, 1])
    with center_col:
        c1, c2, c3 = st.columns(3)
        for i, age in enumerate(AGE_GROUPS):
            if [c1, c2, c3][i % 3].button(age):
                st.session_state.temp_data['age'] = age; st.session_state.page = 'purpose'; st.rerun()
    st.markdown("<div class='back-spacer'></div>", unsafe_allow_html=True)
    _, back_col, _ = st.columns([1, 0.6, 1])
    with back_col:
        st.markdown("<div class='yellow-btn'>", unsafe_allow_html=True)
        if st.button("뒤로 가기"): st.session_state.page = 'gender'; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# [D] 사용자 페이지: 이용 목적
elif st.session_state.page == 'purpose':
    st.markdown("<div class='center-text'><div class='sub-title'>오늘 이용 목적은 무엇인가요?</div></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 6, 1])
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
    st.markdown("<div class='back-spacer'></div>", unsafe_allow_html=True)
    _, back_col, _ = st.columns([1, 0.6, 1])
    with back_col:
        st.markdown("<div class='yellow-btn'>", unsafe_allow_html=True)
        if st.button("뒤로 가기"): st.session_state.page = 'age'; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# [E] 사용자 페이지: 완료
elif st.session_state.page == 'complete':
    st.balloons()
    st.markdown("<div class='center-text' style='margin-top:100px;'><div class='welcome-title'>✅ 접수 완료!</div><div class='sub-title'>감사합니다. 즐거운 시간 되세요!</div></div>", unsafe_allow_html=True)
    time.sleep(2.0)
    st.session_state.page = 'gender'; st.rerun()