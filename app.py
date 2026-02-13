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
    df_init.to_csv(DB_FILE, index=False, encoding="utf-8-sig")

# 세션 기본값
if "is_admin" not in st.session_state:
    if st.query_params.get("admin") == "true":
        st.session_state.is_admin = True
        st.session_state.page = "admin"
    else:
        st.session_state.is_admin = False

if "page" not in st.session_state:
    st.session_state.page = "gender"
if "temp_data" not in st.session_state:
    st.session_state.temp_data = {}

st.set_page_config(page_title="라미그라운드 방명록", layout="wide")

# --- 2. 디자인 (CSS: 모든 수단을 동원한 사이즈 박제) ---
st.markdown(
    """
    <style>
    /* 전체 화면 가로 간격 20px 고정 */
    [data-testid="stHorizontalBlock"] {
        gap: 20px !important;
    }

    /* 1. 사용자 페이지: 메인 버튼 (180x180) 강제 박제 */
    .main-btn-container [data-testid="stButton"] button {
        width: 180px !important;
        height: 180px !important;
        min-width: 180px !important;
        min-height: 180px !important;
        max-width: 180px !important;
        max-height: 180px !important;
        font-size: 24px !important;
        font-weight: 800 !important;
        border-radius: 25px !important;
        display: inline-block !important;
        box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important;
        flex-shrink: 0 !important;
    }

    /* 2. 사용자 페이지: 뒤로 가기 버튼 (180x60, 노란색) 강제 박제 */
    .yellow-btn-area [data-testid="stButton"] button {
        background-color: #FFD700 !important;
        color: #000000 !important;
        width: 180px !important;
        height: 60px !important;
        min-width: 180px !important;
        min-height: 60px !important;
        max-width: 180px !important;
        max-height: 60px !important;
        font-size: 20px !important;
        font-weight: 900 !important;
        border-radius: 12px !important;
        border: 2px solid #CCAC00 !important;
        margin-top: 100px !important; /* 상단 여백 100px */
        display: inline-block !important;
        flex-shrink: 0 !important;
    }

    /* 3. 관리자 페이지 버튼: 직사각형으로 통일 (사용자 버튼의 영향을 받지 않도록 격리) */
    .admin-btn-area [data-testid="stButton"] button {
        height: 50px !important;
        width: 100% !important;
        min-width: 0px !important;
        min-height: 0px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }

    .center-text { text-align: center; padding: 20px; }
    .welcome-title { font-size: 48px; font-weight: 900; margin-bottom: 10px; }
    .sub-title { font-size: 26px; color: #444; margin-bottom: 50px; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 3. 유틸리티 함수 ---
def get_kst_now():
    return datetime.utcnow() + timedelta(hours=9)


def get_korean_weekday(dt: datetime) -> str:
    # Monday=0 ... Sunday=6
    days = ["월", "화", "수", "목", "금", "토", "일"]
    return days[dt.weekday()]


def create_excel_report(df: pd.DataFrame, meta: dict | None = None) -> bytes:
    output = io.BytesIO()

    temp_df = df.copy()
    if temp_df.empty:
        # 빈 데이터도 시트는 생성되도록 처리
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            pd.DataFrame().to_excel(writer, index=False, sheet_name="원본데이터")
            if meta:
                pd.DataFrame([meta]).to_excel(writer, index=False, sheet_name="필터정보")
        return output.getvalue()

    temp_df["일시"] = pd.to_datetime(temp_df["일시"], errors="coerce")

    # 파생 컬럼 (분석/피벗용)
    temp_df["연도"] = temp_df["일시"].dt.year
    temp_df["월"] = temp_df["일시"].dt.month
    temp_df["일자"] = temp_df["일시"].dt.day
    temp_df["시간"] = temp_df["일시"].dt.hour
    temp_df["월-일"] = temp_df["일시"].dt.strftime("%m-%d")
    temp_df["ISO주차"] = temp_df["일시"].dt.isocalendar().week.astype(int)
    temp_df["연-주"] = temp_df["일시"].dt.year.astype(str) + "-W" + temp_df["ISO주차"].astype(str).str.zfill(2)

    # 집계 시트들
    daily = temp_df["월-일"].value_counts().sort_index().reset_index()
    daily.columns = ["월-일", "방문자 수"]

    monthly = temp_df["일시"].dt.to_period("M").astype(str).value_counts().sort_index().reset_index()
    monthly.columns = ["월", "방문자 수"]

    weekly = temp_df["연-주"].value_counts().sort_index().reset_index()
    weekly.columns = ["연-주", "방문자 수"]

    purpose = temp_df["이용목록"].value_counts().reset_index()
    purpose.columns = ["이용목록", "방문자 수"]

    gender = temp_df["성별"].value_counts().reset_index()
    gender.columns = ["성별", "방문자 수"]

    age = temp_df["연령대"].value_counts().reset_index()
    age.columns = ["연령대", "방문자 수"]

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        export_cols = [
            "일시",
            "요일",
            "연도",
            "월",
            "일자",
            "시간",
            "월-일",
            "ISO주차",
            "연-주",
            "성별",
            "연령대",
            "이용목록",
        ]
        existing_cols = [c for c in export_cols if c in temp_df.columns]
        temp_df[existing_cols].to_excel(writer, index=False, sheet_name="원본데이터")

        daily.to_excel(writer, index=False, sheet_name="일자집계(월-일)")
        monthly.to_excel(writer, index=False, sheet_name="월별집계")
        weekly.to_excel(writer, index=False, sheet_name="주별집계(ISO)")
        purpose.to_excel(writer, index=False, sheet_name="목적집계")
        gender.to_excel(writer, index=False, sheet_name="성별집계")
        age.to_excel(writer, index=False, sheet_name="연령집계")

        if meta:
            pd.DataFrame([meta]).to_excel(writer, index=False, sheet_name="필터정보")

    return output.getvalue()


# --- 4. 사이드바(관리자 로그인/로그아웃) ---
with st.sidebar:
    st.title("🛡️ 관리자 메뉴")

    if not st.session_state.is_admin:
        if st.checkbox("관리자 모드 접속"):
            admin_id = st.text_input("아이디")
            admin_pw = st.text_input("비밀번호", type="password")
            if st.button("로그인"):
                # ⚠️ 보안상: 실제 배포 시 secrets/환경변수로 분리 권장
                if admin_id == "jgyouth" and admin_pw == "youth2250!!":
                    st.session_state.is_admin = True
                    st.session_state.page = "admin"
                    st.query_params["admin"] = "true"
                    st.rerun()
                else:
                    st.error("정보가 틀립니다.")
    else:
        st.success("로그인 성공")
        if st.button("로그아웃"):
            st.session_state.is_admin = False
            st.session_state.page = "gender"
            st.query_params.clear()
            st.rerun()

# =========================
# [A] 관리자 페이지
# =========================
if st.session_state.is_admin and st.session_state.page == "admin":
    st.title("📊 데이터 통합 분석 센터")

    df = pd.read_csv(DB_FILE)
    if not df.empty:
        df["일시"] = pd.to_datetime(df["일시"], errors="coerce")

    if not df.empty:
        # 1) 상세 필터링
        with st.expander("🔍 상세 필터링 설정", expanded=True):
            f1, f2 = st.columns(2)
            with f1:
                date_range = st.date_input(
                    "날짜 범위",
                    [df["일시"].min().date(), df["일시"].max().date()],
                )
            with f2:
                selected_gender = st.multiselect("성별", options=["남성", "여성"], default=["남성", "여성"])

            f3, f4 = st.columns(2)
            with f3:
                selected_ages = st.multiselect("연령대", options=AGE_GROUPS, default=AGE_GROUPS)
            with f4:
                selected_purposes = st.multiselect("이용 목적", options=PURPOSES, default=PURPOSES)

        mask = (
            (df["일시"].dt.date >= date_range[0])
            & (df["일시"].dt.date <= date_range[1])
            & (df["성별"].isin(selected_gender))
            & (df["연령대"].isin(selected_ages))
            & (df["이용목록"].isin(selected_purposes))
        )
        f_df = df[mask].copy()

        # 2) 데이터 편집/삭제 테이블
        st.subheader("🗑️ 데이터 편집 및 삭제")
        edited_df = st.data_editor(f_df, num_rows="dynamic", use_container_width=True, key="data_editor")

        # 3) 버튼 영역 (저장 & 엑셀)
        st.markdown("<div class='admin-btn-area'>", unsafe_allow_html=True)
        save_col, excel_col = st.columns(2)

        with save_col:
            if st.button("💾 변경사항 최종 저장", use_container_width=True):
                try:
                    final_df = pd.concat([df[~mask], edited_df], ignore_index=True)
                    final_df[["일시", "요일", "월", "성별", "연령대", "이용목록"]].to_csv(
                        DB_FILE, index=False, encoding="utf-8-sig"
                    )
                    st.success("저장 완료!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")

        with excel_col:
            meta = {
                "시작일": str(date_range[0]),
                "종료일": str(date_range[1]),
                "성별": ", ".join(selected_gender),
                "연령대": ", ".join(selected_ages),
                "이용목적": ", ".join(selected_purposes),
                "추출시각(KST)": get_kst_now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            st.download_button(
                "📥 필터링 데이터 엑셀(원본+집계+필터정보)",
                data=create_excel_report(f_df, meta=meta),
                file_name="현황.xlsx",
                use_container_width=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        if f_df.empty:
            st.info("필터 조건에 해당하는 데이터가 없습니다.")
        else:
            # ---------------------------
            # ✅ 리포트 카드 (월별/주별 요약)
            # ---------------------------
            st.subheader("🧾 리포트 요약")

            temp = f_df.copy()
            temp["일시"] = pd.to_datetime(temp["일시"], errors="coerce")
            temp["날짜"] = temp["일시"].dt.date
            temp["월"] = temp["일시"].dt.to_period("M").astype(str)  # 예: 2026-02
            temp["주"] = temp["일시"].dt.isocalendar().week.astype(int)  # ISO 주차
            temp["연도"] = temp["일시"].dt.year.astype(int)
            temp["연-주"] = temp["연도"].astype(str) + "-W" + temp["주"].astype(str).str.zfill(2)

            total_visits = len(temp)
            daily_avg = round(total_visits / max(1, temp["날짜"].nunique()), 2)

            peak_day_row = temp["날짜"].value_counts().head(1)
            peak_day = str(peak_day_row.index[0]) if len(peak_day_row) else "-"
            peak_day_cnt = int(peak_day_row.iloc[0]) if len(peak_day_row) else 0

            top_purpose_row = temp["이용목록"].value_counts().head(1)
            top_purpose = str(top_purpose_row.index[0]) if len(top_purpose_row) else "-"
            top_purpose_cnt = int(top_purpose_row.iloc[0]) if len(top_purpose_row) else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("총 방문", f"{total_visits:,}명")
            m2.metric("일평균 방문", f"{daily_avg:,}명")
            m3.metric("최다 방문일", peak_day, f"{peak_day_cnt:,}명")
            m4.metric("최다 이용목적", top_purpose, f"{top_purpose_cnt:,}명")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**📌 월별 방문**")
                monthly = temp["월"].value_counts().sort_index().reset_index()
                monthly.columns = ["월", "방문자 수"]
                st.dataframe(monthly, use_container_width=True, hide_index=True)

            with c2:
                st.markdown("**📌 주별 방문(ISO 주차)**")
                weekly = temp["연-주"].value_counts().sort_index().reset_index()
                weekly.columns = ["연-주", "방문자 수"]
                st.dataframe(weekly, use_container_width=True, hide_index=True)

            st.divider()

            # ---------------------------
            # ✅ 일자별 방문 추이 (x축 월-일 표시)
            # ---------------------------
            st.subheader("📅 일자별 방문 추이")
            daily_counts = (
                f_df["일시"].dt.floor("D")
                .value_counts()
                .sort_index()
                .reset_index()
            )
            daily_counts.columns = ["날짜", "방문자 수"]

            fig_daily = px.line(daily_counts, x="날짜", y="방문자 수", markers=True)
            fig_daily.update_xaxes(
                tickformat="%m-%d",  # ✅ 월-일
                dtick="D1",
                title_text="월-일",
            )
            st.plotly_chart(fig_daily, use_container_width=True)

            # ---------------------------
            # ✅ 시간대별 혼잡도 (요일 x 시간) 히트맵
            # ---------------------------
            st.subheader("🕒 시간대별 혼잡도 (요일 × 시간)")
            heat = f_df.copy()
            heat["일시"] = pd.to_datetime(heat["일시"], errors="coerce")
            heat["시간"] = heat["일시"].dt.hour

            # 요일이 과거 데이터 때문에 영문/한글 섞일 수 있으면, 아래 한 줄로 재계산도 가능
            # heat["요일"] = heat["일시"].apply(get_korean_weekday)

            weekday_order = ["월", "화", "수", "목", "금", "토", "일"]
            pivot = (
                heat.pivot_table(index="요일", columns="시간", values="일시", aggfunc="count", fill_value=0)
                .reindex(weekday_order)
            )

            fig_heat = px.imshow(
                pivot,
                aspect="auto",
                labels=dict(x="시간(시)", y="요일", color="방문자 수"),
            )
            st.plotly_chart(fig_heat, use_container_width=True)

            # ---------------------------
            # ✅ 기본 파이 차트
            # ---------------------------
            r1, r2 = st.columns(2)
            with r1:
                st.plotly_chart(px.pie(f_df, names="성별", title="성별 비중", hole=0.4), use_container_width=True)
            with r2:
                st.plotly_chart(px.pie(f_df, names="이용목록", title="이용 목적 비중", hole=0.4), use_container_width=True)

    else:
        st.info("데이터가 없습니다.")

# =========================
# [B] 사용자 페이지: 성별
# =========================
elif st.session_state.page == "gender":
    st.markdown(
        "<div class='center-text'><div class='welcome-title'>라미그라운드 방문을 환영합니다! 😊</div>"
        "<div class='sub-title'>성별을 선택해주세요.</div></div>",
        unsafe_allow_html=True,
    )
    _, center_col, _ = st.columns([1, 4, 1])
    with center_col:
        st.markdown("<div class='main-btn-container'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("남성", key="m"):
            st.session_state.temp_data["gender"] = "남성"
            st.session_state.page = "age"
            st.rerun()
        if c2.button("여성", key="f"):
            st.session_state.temp_data["gender"] = "여성"
            st.session_state.page = "age"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# =========================
# [C] 사용자 페이지: 연령대
# =========================
elif st.session_state.page == "age":
    st.markdown("<div class='center-text'><div class='sub-title'>연령대를 선택해주세요.</div></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 6, 1])
    with center_col:
        st.markdown("<div class='main-btn-container'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        for i, age in enumerate(AGE_GROUPS):
            if [c1, c2, c3][i % 3].button(age, key=f"age_{i}"):
                st.session_state.temp_data["age"] = age
                st.session_state.page = "purpose"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 뒤로 가기
    _, back_col, _ = st.columns([1, 1, 1])
    with back_col:
        st.markdown("<div class='yellow-btn-area'>", unsafe_allow_html=True)
        if st.button("뒤로 가기", key="back_to_gender"):
            st.session_state.page = "gender"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# =========================
# [D] 사용자 페이지: 이용 목적
# =========================
elif st.session_state.page == "purpose":
    st.markdown("<div class='center-text'><div class='sub-title'>오늘 이용 목적은 무엇인가요?</div></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 6, 1])
    with center_col:
        st.markdown("<div class='main-btn-container'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        for i, purp in enumerate(PURPOSES):
            if [c1, c2, c3][i % 3].button(purp, key=f"purp_{i}"):
                now = get_kst_now()
                new_row = {
                    "일시": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "요일": get_korean_weekday(now),  # ✅ 한글 요일
                    "월": now.month,
                    "성별": st.session_state.temp_data["gender"],
                    "연령대": st.session_state.temp_data["age"],
                    "이용목록": purp,
                }
                df = pd.read_csv(DB_FILE)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
                st.session_state.page = "complete"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 뒤로 가기
    _, back_col, _ = st.columns([1, 1, 1])
    with back_col:
        st.markdown("<div class='yellow-btn-area'>", unsafe_allow_html=True)
        if st.button("뒤로 가기", key="back_to_age"):
            st.session_state.page = "age"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# =========================
# [E] 사용자 페이지: 완료
# =========================
elif st.session_state.page == "complete":
    st.balloons()
    st.markdown(
        "<div class='center-text' style='margin-top:100px;'>"
        "<div class='welcome-title'>✅ 접수 완료!</div>"
        "<div class='sub-title'>감사합니다. 즐거운 시간 되세요!</div></div>",
        unsafe_allow_html=True,
    )
    time.sleep(2.0)
    st.session_state.page = "gender"
    st.rerun()
