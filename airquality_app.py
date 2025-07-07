
import streamlit as st
import pandas as pd
import os
import folium
from streamlit.components.v1 import html

st.set_page_config(
    page_title="Korea City Air Quality Dashboard",
    page_icon=":sunny:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 하늘색 배경 + 짙은 파란색 텍스트 + 버튼 색상
st.markdown(
    """
    <style>
        html, body, [class*="css"], .stApp {
            background-color:#E6F7FF;
        }
        h1, h2, h3, h4, h5, h6, .stMetricValue, .stMetricLabel {
            color:#004C99;
        }
        .stButton>button {
            background-color:#1E90FF !important;
            color:white !important;
            border:none;
            border-radius:6px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌤️ 하늘색 테마 대기질 대시보드")
st.markdown("데이터 파일이 필요합니다. 실제 앱에서는 데이터 로딩 후 시각화가 실행됩니다.")

# 사이드바에 오염물질 설명 추가
with st.sidebar.expander("📌 오염물질이 건강에 미치는 영향"):
    st.markdown("""
    - **PM2.5 (초미세먼지)**: 폐 깊숙이 침투하여 **호흡기, 심혈관질환**을 유발하며, WHO 지정 **1급 발암물질**입니다.
    - **PM10 (미세먼지)**: 기관지 자극, 천식 및 호흡기 질환 악화.
    - **NO₂ (이산화질소)**: 기관지염, 천식 악화. 자동차 배기가스의 주요 성분.
    - **SO₂ (아황산가스)**: **눈과 점막 자극**, 폐기능 저하, 산성비 유발.
    - **CO (일산화탄소)**: 산소 운반 방해 → 고농도 흡입 시 **두통, 의식 저하, 사망 가능**.
    """)

st.markdown("## 🧠 오염물질 설명")

cols = st.columns(3)
cols[0].info("**PM2.5 (초미세먼지)**\n\n폐 깊숙이 침투 → 심혈관질환 및 암 유발")
cols[1].info("**PM10 (미세먼지)**\n\n코·기관지 자극 → 호흡기 악화")
cols[2].info("**NO₂ (이산화질소)**\n\n천식, 기관지염 악화")

cols = st.columns(2)
cols[0].info("**SO₂ (아황산가스)**\n\n점막 자극, 산성비 원인")
cols[1].info("**CO (일산화탄소)**\n\n산소 결합 방해 → 고농도 노출 시 치명적")
