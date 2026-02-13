import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import os
import io
import time
import streamlit.components.v1 as components
from typing import Optional, Dict, Any

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

# --- 2. CSS (기본 디자인) ---
st.markdown(
    """
    <style>
    [data-testid="stHorizontalBlock"] { gap: 20px !important; }
    .center-text { text-align: center; padding: 20px; }
    .welcome-title { font-size: 48px; font-weight: 900; margin-bottom: 10px; }
    .sub-title { font-size: 26px; color: #444; margin-bottom: 50px; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 2-1. 버튼 사이즈 강제 고정 (JS: Streamlit DOM 변화에도 유지) ---
def inject_button_sizer():
    kiosk_texts = ["남성", "여성"] + AGE_GROUPS + PURPOSES
    kiosk_js_array = "[" + ",".join([f'"{t}"' for t in kiosk_texts]) + "]"

    admin_texts = [
        "💾 변경사항 최종 저장",
        "📥 필터링 데이터 엑셀(원본+집계+필터정보)",
        "로그인",
        "로그아웃",
    ]
    admin_js_array = "[" + ",".join([f'"{t}"' for t in admin_texts]) + "]"

    page = st.session_state.get("page", "gender")
    is_admin = bool(st.session_state.get("is_admin", False))
    is_admin_page_js = "true" if (is_admin and page == "admin") else "false"

    components.html(
        f"""
        <script>
        (function() {{
            const kioskTexts = {kiosk_js_array};
            const adminTexts = {admin_js_array};
            const isAdminPage = {is_admin_page_js};

            function applyStyles() {{
                const main = window.parent.document.querySelector('[data-testid="stMain"]');
                if (!main) return;

                const buttons = main.querySelectorAll('button');
                buttons.forEach(btn => {{
                    const t = (btn.innerText || "").trim();

                    // reset
                    btn.style.width = "";
                    btn.style.height = "";
                    btn.style.minWidth = "";
                    btn.style.minHeight = "";
                    btn.style.maxWidth = "";
                    btn.style.maxHeight = "";
                    btn.style.fontSize = "";
                    btn.style.fontWeight = "";
                    btn.style.borderRadius = "";
                    btn.style.display = "";
                    btn.style.alignItems = "";
                    btn.style.justifyContent = "";
                    btn.style.boxShadow = "";
                    btn.style.backgroundColor = "";
                    btn.style.color = "";
                    btn.style.border = "";

                    if (isAdminPage) {{
                        if (adminTexts.includes(t)) {{
                            btn.style.height = "50px";
                            btn.style.fontSize = "16px";
                            btn.style.fontWeight = "600";
                            btn.style.borderRadius = "8px";
                        }}
                        return;
                    }}

                    if (kioskTexts.includes(t)) {{
                        btn.style.width = "180px";
                        btn.style.height = "180px";
                        btn.style.minWidth = "180px";
                        btn.style.minHeight = "180px";
                        btn.style.maxWidth = "180px";
                        btn.style.maxHeight = "180px";
                        btn.style.fontSize = "24px";
                        btn.style.fontWeight = "800";
                        btn.style.borderRadius = "25px";
                        btn.style.display = "flex";
                        btn.style.alignItems = "center";
                        btn.style.justifyContent = "center";
                        btn.style.boxShadow = "0 6px 14px rgba(0,0,0,0.15)";
                    }}

                    if (t === "뒤로 가기") {{
                        btn.style.width = "180px";
                        btn.style.height = "60px";
                        btn.style.minWidth = "180px";
                        btn.style.minHeight = "60px";
                        btn.style.maxWidth = "180px";
                        btn.style.maxHeight = "60px";
                        btn.style.fontSize = "20px";
                        btn.style.fontWeight = "900";
                        btn.style.borderRadius = "12px";
                        btn.style.backgroundColor = "#FFD700";
                        btn.style.color = "#000";
                        btn.style.border = "2px solid #CCAC00";
                        btn.style.boxShadow = "0 6px 14px rgba(0,0,0,0.12)";
                    }}
                }});
            }}

            applyStyles();
            setTimeout(applyStyles, 50);
            setTimeout(applyStyles, 200);
            setTimeout(applyStyles, 500);

            const root = window.parent.document.body;
            if (root && !window.parent.__kioskButtonObserver) {{
                const obs = new MutationObserver(() => applyStyles());
                obs.observe(root, {{ childList: true, subtree: true }});
                window.parent.__kioskButtonObserver = obs;
            }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )

inject_button_sizer()

# --- 3. 유틸리티 함수 ---
def get_kst_now() -> datetime:
    return datetime.utcnow() + timedelta(hours=9)

def get_korean_weekday(dt: datetime) -> str:
    days = ["월", "화", "수", "목", "금", "토", "일"]
    return days[dt.weekday()]

def iso_week_date_range(year: int, week: int) -> tuple[date, date]:
    start = date.fromisocalendar(year, week, 1)
    end = date.fromisocalendar(year, week, 7)
    return start, end

def create_excel_report(df: pd.DataFrame, meta: Optional[Dict[str, Any]] = None) -> bytes:
    output = io.BytesIO()

    temp_df = df.copy()
    if temp_df.empty:
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            pd.DataFrame().to_excel(writer, index=False, sheet_name="원본데이터")
            if meta:
                pd.DataFrame([meta]).to_excel(writer, index=False, sheet_name="필터정보")
        return output.getvalue()

    temp_df["일시"] = pd.to_datetime(temp_df["일시"], errors="coerce")

    temp_df["연도"] = temp_df["일시"].dt.year
    temp_df["월"] = temp_df["일시"].dt.month
    temp_df["일자"] = temp_df["일시"].dt.day
    temp_df["시간"] = temp_df["일시"].dt.hour
    temp_df["월-일"] = temp_df["일시"].dt.strftime("%m-%d")

    iso = temp_df["일시"].dt.isocalendar()
    temp_df["ISO연도"] = iso.year.astype(int)
    temp_df["ISO주차"] = iso.week.astype(int)
    temp_df["연-주"] = temp_df["ISO연도"].astype(str) + "-W" + temp_df["ISO주차"].astype(str).str.zfill(2)

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
            "일시", "요일",
            "연도", "월", "일자", "시간",
            "월-일", "ISO연도", "ISO주차", "연-주",
            "성별", "연령대", "이용목록",
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

    if df.empty:
        st.info("데이터가 없습니다.")
    else:
        # ============================================================
        # ✅ 1) 데이터 편집/삭제 (상세 필터링과 무관하게 '전체 데이터' 대상)
        #    - 아래에서 저장/다운로드도 전체 데이터 기준
        # ============================================================
        st.subheader("🗑️ 데이터 편집 및 삭제 (전체 데이터)")
        df_all = df.copy()

        edited_all_df = st.data_editor(
            df_all,
            num_rows="dynamic",
            use_container_width=True,
            key="data_editor_all",
        )

        save_col, excel_col = st.columns(2)
        with save_col:
            if st.button("💾 변경사항 최종 저장", use_container_width=True, key="save_all"):
                try:
                    # 필요한 컬럼만 저장(구조 유지)
                    cols = ["일시", "요일", "월", "성별", "연령대", "이용목록"]
                    for c in cols:
                        if c not in edited_all_df.columns:
                            edited_all_df[c] = None
                    edited_all_df[cols].to_csv(DB_FILE, index=False, encoding="utf-8-sig")
                    st.success("저장 완료!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")

        with excel_col:
            meta_all = {
                "대상": "전체 데이터(편집/삭제 섹션 기준)",
                "추출시각(KST)": get_kst_now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            st.download_button(
                "📥 전체 데이터 엑셀(원본+집계)",
                data=create_excel_report(df_all, meta=meta_all),
                file_name="전체데이터_현황.xlsx",
                use_container_width=True,
                key="download_all_excel",
            )

        st.divider()

        # ============================================================
        # ✅ 2) 상세 필터링 설정 (리포트/그래프/파이차트/필터엑셀은 여기만 반영)
        # ============================================================
        st.subheader("🔍 상세 필터링 설정 (리포트/그래프용)")
        with st.expander("필터 열기/닫기", expanded=True):
            f1, f2 = st.columns(2)
            with f1:
                date_range = st.date_input(
                    "날짜 범위",
                    [df["일시"].min().date(), df["일시"].max().date()],
                    key="filter_date_range",
                )
            with f2:
                selected_gender = st.multiselect(
                    "성별",
                    options=["남성", "여성"],
                    default=["남성", "여성"],
                    key="filter_gender",
                )

            f3, f4 = st.columns(2)
            with f3:
                selected_ages = st.multiselect(
                    "연령대",
                    options=AGE_GROUPS,
                    default=AGE_GROUPS,
                    key="filter_ages",
                )
            with f4:
                selected_purposes = st.multiselect(
                    "이용 목적",
                    options=PURPOSES,
                    default=PURPOSES,
                    key="filter_purposes",
                )

        mask = (
            (df["일시"].dt.date >= date_range[0])
            & (df["일시"].dt.date <= date_range[1])
            & (df["성별"].isin(selected_gender))
            & (df["연령대"].isin(selected_ages))
            & (df["이용목록"].isin(selected_purposes))
        )
        f_df = df[mask].copy()

        # 필터링 엑셀 다운로드(리포트용)
        meta_filtered = {
            "대상": "필터링 데이터(리포트/그래프 기준)",
            "시작일": str(date_range[0]),
            "종료일": str(date_range[1]),
            "성별": ", ".join(selected_gender),
            "연령대": ", ".join(selected_ages),
            "이용목적": ", ".join(selected_purposes),
            "추출시각(KST)": get_kst_now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        st.download_button(
            "📥 필터링 데이터 엑셀(원본+집계+필터정보)",
            data=create_excel_report(f_df, meta=meta_filtered),
            file_name="필터링_현황.xlsx",
            use_container_width=True,
            key="download_filtered_excel",
        )

        st.divider()

        if f_df.empty:
            st.info("필터 조건에 해당하는 데이터가 없습니다.")
        else:
            # ---------------------------
            # ✅ 리포트 요약 (필터 반영)
            # ---------------------------
            st.subheader("🧾 리포트 요약")

            temp = f_df.copy()
            temp["일시"] = pd.to_datetime(temp["일시"], errors="coerce")
            temp = temp.dropna(subset=["일시"])
            temp["날짜"] = temp["일시"].dt.date
            temp["월"] = temp["일시"].dt.to_period("M").astype(str)

            iso = temp["일시"].dt.isocalendar()
            temp["ISO연도"] = iso.year.astype(int)
            temp["ISO주차"] = iso.week.astype(int)

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
                st.markdown("**📌 주별 방문 (ISO 주차 + 기간)**")
                weekly_raw = (
                    temp.groupby(["ISO연도", "ISO주차"])
                    .size()
                    .reset_index(name="방문자 수")
                    .sort_values(["ISO연도", "ISO주차"])
                )

                def make_week_label(row):
                    y = int(row["ISO연도"])
                    w = int(row["ISO주차"])
                    s, e = iso_week_date_range(y, w)
                    return f"{y}-W{w:02d} ({s.isoformat()}~{e.isoformat()})"

                weekly_raw["주(기간)"] = weekly_raw.apply(make_week_label, axis=1)
                weekly = weekly_raw[["주(기간)", "방문자 수"]]
                st.dataframe(weekly, use_container_width=True, hide_index=True)

            st.divider()

            # ---------------------------
            # ✅ 일자별 방문 추이 (필터 반영 + 기간 선택)
            #    - x축: 2/3 형태
            #    - 자동 간격: 5일 / 1달
            # ---------------------------
            st.subheader("📅 일자별 방문 추이")

            f_df2 = f_df.copy()
            f_df2["일시"] = pd.to_datetime(f_df2["일시"], errors="coerce")
            f_df2 = f_df2.dropna(subset=["일시"])

            if f_df2.empty:
                st.info("그래프를 그릴 데이터가 없습니다(일시 파싱 실패 또는 데이터 없음).")
            else:
                f_min = f_df2["일시"].min().date()
                f_max = f_df2["일시"].max().date()

                period_option = st.radio(
                    "조회 기간",
                    options=["최근 1주", "최근 1달", "기간 설정"],
                    horizontal=True,
                    key="trend_period",
                )

                if period_option == "기간 설정":
                    chart_range = st.date_input(
                        "그래프 기간(필터 결과 범위 내에서 선택)",
                        value=[f_min, f_max],
                        min_value=f_min,
                        max_value=f_max,
                        key="trend_range",
                    )
                    if isinstance(chart_range, (list, tuple)) and len(chart_range) == 2:
                        chart_start, chart_end = chart_range[0], chart_range[1]
                    else:
                        chart_start, chart_end = f_min, f_max
                else:
                    today_kst = get_kst_now().date()
                    if period_option == "최근 1주":
                        chart_start = max(today_kst - timedelta(days=6), f_min)
                        chart_end = min(today_kst, f_max)
                    else:
                        chart_start = max(today_kst - timedelta(days=29), f_min)
                        chart_end = min(today_kst, f_max)

                chart_df = f_df2[(f_df2["일시"].dt.date >= chart_start) & (f_df2["일시"].dt.date <= chart_end)].copy()

                if chart_df.empty:
                    st.info("선택한 기간에 해당하는 데이터가 없습니다.")
                else:
                    daily_counts = (
                        chart_df.assign(날짜=chart_df["일시"].dt.floor("D"))
                        .groupby("날짜")
                        .size()
                        .reset_index(name="방문자 수")
                        .sort_values("날짜")
                    )

                    fig_daily = px.line(
                        daily_counts,
                        x="날짜",
                        y="방문자 수",
                        markers=True,
                        hover_data={"날짜": "|%Y-%m-%d"},
                    )

                    fig_daily.update_xaxes(
                        tickformat="%-m/%-d",  # 2/3 형태(환경에 따라 02/03로 보일 수 있음)
                        title_text="날짜",
                    )

                    total_days = (chart_end - chart_start).days + 1
                    if total_days >= 120:
                        fig_daily.update_xaxes(dtick="M1", tickformat="%Y/%m")
                    elif total_days >= 35:
                        fig_daily.update_xaxes(dtick="D5", tickformat="%-m/%-d")
                    else:
                        fig_daily.update_xaxes(dtick="D1", tickformat="%-m/%-d")

                    st.plotly_chart(fig_daily, use_container_width=True)

            # ---------------------------
            # ✅ 파이 차트(필터 반영)
            # ---------------------------
            r1, r2 = st.columns(2)
            with r1:
                st.plotly_chart(px.pie(f_df, names="성별", title="성별 비중", hole=0.4), use_container_width=True)
            with r2:
                st.plotly_chart(px.pie(f_df, names="이용목록", title="이용 목적 비중", hole=0.4), use_container_width=True)

# =========================
# [B] 사용자 페이지: 성별
# =========================
elif st.session_state.page == "gender":
    st.markdown(
        "<div class='center-text'>"
        "<div class='welcome-title'>라미그라운드 방문을 환영합니다! 😊</div>"
        "<div class='sub-title'>성별을 선택해주세요.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    _, center_col, _ = st.columns([1, 4, 1])
    with center_col:
        c1, c2 = st.columns(2)
        if c1.button("남성", key="m"):
            st.session_state.temp_data["gender"] = "남성"
            st.session_state.page = "age"
            st.rerun()
        if c2.button("여성", key="f"):
            st.session_state.temp_data["gender"] = "여성"
            st.session_state.page = "age"
            st.rerun()

# =========================
# [C] 사용자 페이지: 연령대
# =========================
elif st.session_state.page == "age":
    st.markdown(
        "<div class='center-text'><div class='sub-title'>연령대를 선택해주세요.</div></div>",
        unsafe_allow_html=True,
    )
    _, center_col, _ = st.columns([1, 6, 1])
    with center_col:
        c1, c2, c3 = st.columns(3)
        for i, age in enumerate(AGE_GROUPS):
            if [c1, c2, c3][i % 3].button(age, key=f"age_{i}"):
                st.session_state.temp_data["age"] = age
                st.session_state.page = "purpose"
                st.rerun()

    _, back_col, _ = st.columns([1, 1, 1])
    with back_col:
        if st.button("뒤로 가기", key="back_to_gender"):
            st.session_state.page = "gender"
            st.rerun()

# =========================
# [D] 사용자 페이지: 이용 목적
# =========================
elif st.session_state.page == "purpose":
    st.markdown(
        "<div class='center-text'><div class='sub-title'>오늘 이용 목적은 무엇인가요?</div></div>",
        unsafe_allow_html=True,
    )
    _, center_col, _ = st.columns([1, 6, 1])
    with center_col:
        c1, c2, c3 = st.columns(3)
        for i, purp in enumerate(PURPOSES):
            if [c1, c2, c3][i % 3].button(purp, key=f"purp_{i}"):
                now = get_kst_now()
                new_row = {
                    "일시": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "요일": get_korean_weekday(now),
                    "월": now.month,
                    "성별": st.session_state.temp_data["gender"],
                    "연령대": st.session_state.temp_data["age"],
                    "이용목록": purp,
                }
                df2 = pd.read_csv(DB_FILE)
                df2 = pd.concat([df2, pd.DataFrame([new_row])], ignore_index=True)
                df2.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
                st.session_state.page = "complete"
                st.rerun()

    _, back_col, _ = st.columns([1, 1, 1])
    with back_col:
        if st.button("뒤로 가기", key="back_to_age"):
            st.session_state.page = "age"
            st.rerun()

# =========================
# [E] 사용자 페이지: 완료
# =========================
elif st.session_state.page == "complete":
    st.balloons()
    st.markdown(
        "<div class='center-text' style='margin-top:100px;'>"
        "<div class='welcome-title'>✅ 접수 완료!</div>"
        "<div class='sub-title'>감사합니다. 즐거운 시간 되세요!</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    time.sleep(2.0)
    st.session_state.page = "gender"
    st.rerun()
