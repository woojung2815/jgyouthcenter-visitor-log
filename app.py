import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import io

# --- 1. 기본 설정 및 데이터 로드 ---
DB_FILE = "visitor_log.csv"
LOCATIONS = ["라미라운지", "라미그라운드", "라미의숲", "라미스튜디오", "라미의방", "복합문화공간", "강의실", "체육관"]
AGE_GROUPS = ["아동", "초등", "중등", "고등", "24세 이하 성인", "25세 이상 성인"]

# 데이터 파일이 없으면 새로 생성
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["일시", "요일", "시간", "성별", "연령대", "이용목록"])
    df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# 세션 상태 초기화
if 'page' not in st.session_state:
    st.session_state.page = 'gender'
if 'temp_data' not in st.session_state:
    st.session_state.temp_data = {}

st.set_page_config(page_title="라미그라운드 방명록 시스템", layout="wide")

# --- 2. 엑셀 파일 생성 함수 (그래프 포함) ---
def create_excel_report(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 데이터 시트
        df.to_excel(writer, index=False, sheet_name='방문기록_리스트')
        workbook  = writer.book
        worksheet = writer.sheets['방문기록_리스트']
        worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
        
        # 통계 시트 및 차트
        summary_df = df['이용목록'].value_counts().reset_index()
        summary_df.columns = ['장소', '방문수']
        summary_df.to_excel(writer, index=False, sheet_name='통계_요약')
        
        stats_sheet = writer.sheets['통계_요약']
        chart = workbook.add_chart({'type': 'pie'})
        chart.add_series({
            'name': '장소별 이용 비중',
            'categories': ['통계_요약', 1, 0, len(summary_df), 0],
            'values':     ['통계_요약', 1, 1, len(summary_df), 1],
            'data_labels': {'percentage': True, 'position': 'outside_end'},
        })
        chart.set_title({'name': '장소별 이용 현황 (%)'})
        stats_sheet.insert_chart('D2', chart)
    return output.getvalue()

# --- 3. 사이드바 (관리자 로그인) ---
with st.sidebar:
    st.title("🛡️ 센터 관리")
    if st.checkbox("관리자 모드 접속"):
        admin_id = st.text_input("아이디")
        admin_pw = st.text_input("비밀번호", type="password")
        if admin_id == "jgyouth" and admin_pw == "youth2250!!":
            st.success("로그인 성공")
            st.session_state.page = 'admin'
        else:
            if admin_id or admin_pw:
                st.error("계정 정보가 틀립니다.")
    else:
        if st.session_state.page == 'admin':
            st.session_state.page = 'gender'

# --- 4. 메인 화면 로직 ---

# [A] 관리자 페이지
if st.session_state.page == 'admin':
    st.title("📊 라미그라운드 이용 현황 대시보드")
    df = pd.read_csv(DB_FILE)
    df['일시'] = pd.to_datetime(df['일시'])
    
    if not df.empty:
        # 엑셀 다운로드 버튼
        excel_file = create_excel_report(df)
        st.download_button(
            label="📥 전체 통계 엑셀 다운로드 (.xlsx)",
            data=excel_file,
            file_name=f"라미그라운드_이용현황_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        
        st.divider()
        
        # KPI 카드
        c1, c2, c3 = st.columns(3)
        c1.metric("누적 방문자", f"{len(df)}명")
        today_df = df[df['일시'].dt.date == datetime.now().date()]
        c2.metric("오늘 방문자", f"{len(today_df)}명")
        c3.metric("최고 인기 장소", df['이용목록'].value_counts().idxmax())

        # 시각화 그래프
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("📍 장소별 이용 비중")
            fig_pie = px.pie(df, names='이용목록', hole=0.3, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.subheader("📅 요일별 방문 추이")
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_counts = df['요일'].value_counts().reindex(day_order).fillna(0)
            st.bar_chart(day_counts)

        with col_right:
            st.subheader("👥 연령대별 방문 분포")
            fig_age = px.bar(df['연령대'].value_counts().reset_index(), x='연령대', y='count', color='연령대')
            st.plotly_chart(fig_age, use_container_width=True)
            
            st.subheader("⏰ 시간대별 혼잡도")
            hour_counts = df['시간'].value_counts().sort_index()
            st.line_chart(hour_counts)

        # 상세 데이터 표
        with st.expander("🔍 상세 방문 로그 보기"):
            st.dataframe(df.sort_values(by="일시", ascending=False), use_container_width=True)
    else:
        st.info("현재 기록된 데이터가 없습니다.")

# [B] 사용자 페이지 - 성별 선택
elif st.session_state.page == 'gender':
    st.title("중구청소년센터 방문을 환영합니다! 😊")
    st.markdown("### 성별을 선택해 주세요.")
    col1, col2 = st.columns(2)
    if col1.button("남성", use_container_width=True, type="primary"):
        st.session_state.temp_data['gender'] = "남성"
        st.session_state.page = 'age'
        st.rerun()
    if col2.button("여성", use_container_width=True, type="primary"):
        st.session_state.temp_data['gender'] = "여성"
        st.session_state.page = 'age'
        st.rerun()

# [C] 사용자 페이지 - 연령대 선택
elif st.session_state.page == 'age':
    st.title("연령대를 선택해 주세요.")
    cols = st.columns(2)
    for i, age in enumerate(AGE_GROUPS):
        if cols[i % 2].button(age, use_container_width=True):
            st.session_state.temp_data['age'] = age
            st.session_state.page = 'location'
            st.rerun()

# [D] 사용자 페이지 - 이용 장소 선택
elif st.session_state.page == 'location':
    st.title("이용하실 곳을 선택해 주세요.")
    cols = st.columns(2)
    for i, loc in enumerate(LOCATIONS):
        if cols[i % 2].button(loc, use_container_width=True):
            # 데이터 저장
            now = datetime.now()
            new_row = {
                "일시": now.strftime("%Y-%m-%d %H:%M:%S"),
                "요일": now.strftime("%A"),
                "시간": now.hour,
                "성별": st.session_state.temp_data['gender'],
                "연령대": st.session_state.temp_data['age'],
                "이용목록": loc
            }
            df = pd.read_csv(DB_FILE)
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
            
            st.session_state.page = 'complete'
            st.rerun()

# [E] 사용자 페이지 - 완료 알림
elif st.session_state.page == 'complete':
    st.balloons()
    st.title("✅ 접수가 완료되었습니다!")
    st.success(f"{st.session_state.temp_data['age']} 즐거운 시간 되세요!")
    st.info("3초 후 처음 화면으로 돌아갑니다...")
    import time
    time.sleep(3)
    st.session_state.page = 'gender'
    st.rerun()