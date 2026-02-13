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

# --- 2. CSS ---
st.markdown("""
<style>
[data-testid="stHorizontalBlock"] { gap: 20px !important; }
.center-text { text-align: center; padding: 20px; }
.welcome-title { font-size: 48px; font-weight: 900; margin-bottom: 10px; }
.sub-title { font-size: 26px; color: #444; margin-bottom: 50px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 버튼 사이즈 강제 ---
def inject_button_sizer():
    kiosk_texts = ["남성","여성"] + AGE_GROUPS + PURPOSES
    kiosk_js_array = "[" + ",".join([f'"{t}"' for t in kiosk_texts]) + "]"

    admin_texts = [
        "💾 변경사항 최종 저장",
        "📥 전체 데이터 엑셀(원본+집계)",
        "📥 필터링 데이터 엑셀(원본+집계+필터정보)",
        "로그인","로그아웃",
    ]
    admin_js_array = "[" + ",".join([f'"{t}"' for t in admin_texts]) + "]"

    page = st.session_state.get("page","gender")
    is_admin = bool(st.session_state.get("is_admin",False))
    is_admin_page_js = "true" if (is_admin and page=="admin") else "false"

    components.html(f"""
<script>
(function(){{
const kioskTexts={kiosk_js_array};
const adminTexts={admin_js_array};
const isAdminPage={is_admin_page_js};

function applyStyles(){{
 const main=window.parent.document.querySelector('[data-testid="stMain"]');
 if(!main) return;
 const buttons=main.querySelectorAll('button');

 buttons.forEach(btn=>{{
  const t=(btn.innerText||"").trim();

  btn.style.width="";
  btn.style.height="";
  btn.style.marginTop="";
  btn.style.backgroundColor="";
  btn.style.color="";
  btn.style.border="";

  if(isAdminPage){{
    if(adminTexts.includes(t)){{
      btn.style.height="50px";
      btn.style.fontSize="16px";
      btn.style.borderRadius="8px";
    }}
    return;
  }}

  if(kioskTexts.includes(t)){{
    btn.style.width="180px";
    btn.style.height="180px";
    btn.style.fontSize="24px";
    btn.style.fontWeight="800";
    btn.style.borderRadius="25px";
    btn.style.display="flex";
    btn.style.alignItems="center";
    btn.style.justifyContent="center";
    btn.style.boxShadow="0 6px 14px rgba(0,0,0,0.15)";
  }}

  // 뒤로가기 버튼 (노란색 제거 + 간격만)
  if(t==="뒤로 가기"){{
    btn.style.width="180px";
    btn.style.height="60px";
    btn.style.fontSize="20px";
    btn.style.fontWeight="800";
    btn.style.borderRadius="12px";
    btn.style.marginTop="30px";   // ← 세로 간격 30px
  }}
 }});
}}

applyStyles();
setTimeout(applyStyles,50);
setTimeout(applyStyles,300);

const root=window.parent.document.body;
if(root && !window.parent.__btnObs){{
 const obs=new MutationObserver(()=>applyStyles());
 obs.observe(root,{{childList:true,subtree:true}});
 window.parent.__btnObs=obs;
}}
})();
</script>
""",height=0,width=0)

inject_button_sizer()

# --- 유틸 ---
def get_kst_now():
    return datetime.utcnow()+timedelta(hours=9)

def get_korean_weekday(dt):
    return ["월","화","수","목","금","토","일"][dt.weekday()]

# =========================
# 사용자 페이지
# =========================
if st.session_state.page=="gender":
    st.markdown("<div class='center-text'><div class='welcome-title'>라미그라운드 방문을 환영합니다 😊</div><div class='sub-title'>성별을 선택해주세요</div></div>",unsafe_allow_html=True)
    _,c,_=st.columns([1,4,1])
    with c:
        c1,c2=st.columns(2)
        if c1.button("남성"):
            st.session_state.temp_data["gender"]="남성"
            st.session_state.page="age"
            st.rerun()
        if c2.button("여성"):
            st.session_state.temp_data["gender"]="여성"
            st.session_state.page="age"
            st.rerun()

elif st.session_state.page=="age":
    st.markdown("<div class='center-text'><div class='sub-title'>연령대를 선택해주세요</div></div>",unsafe_allow_html=True)
    _,c,_=st.columns([1,6,1])
    with c:
        c1,c2,c3=st.columns(3)
        for i,a in enumerate(AGE_GROUPS):
            if [c1,c2,c3][i%3].button(a):
                st.session_state.temp_data["age"]=a
                st.session_state.page="purpose"
                st.rerun()
    _,b,_=st.columns([1,1,1])
    with b:
        if st.button("뒤로 가기"):
            st.session_state.page="gender"
            st.rerun()

elif st.session_state.page=="purpose":
    st.markdown("<div class='center-text'><div class='sub-title'>오늘 이용 목적은?</div></div>",unsafe_allow_html=True)
    _,c,_=st.columns([1,6,1])
    with c:
        c1,c2,c3=st.columns(3)
        for i,p in enumerate(PURPOSES):
            if [c1,c2,c3][i%3].button(p):
                now=get_kst_now()
                new_row={
                    "일시":now.strftime("%Y-%m-%d %H:%M:%S"),
                    "요일":get_korean_weekday(now),
                    "월":now.month,
                    "성별":st.session_state.temp_data["gender"],
                    "연령대":st.session_state.temp_data["age"],
                    "이용목록":p
                }
                df=pd.read_csv(DB_FILE)
                df=pd.concat([df,pd.DataFrame([new_row])],ignore_index=True)
                df.to_csv(DB_FILE,index=False,encoding="utf-8-sig")
                st.session_state.page="complete"
                st.rerun()
    _,b,_=st.columns([1,1,1])
    with b:
        if st.button("뒤로 가기"):
            st.session_state.page="age"
            st.rerun()

elif st.session_state.page=="complete":
    st.balloons()
    st.markdown("<div class='center-text' style='margin-top:100px;'><div class='welcome-title'>접수 완료!</div></div>",unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.page="gender"
    st.rerun()
