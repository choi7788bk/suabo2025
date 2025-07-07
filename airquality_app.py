
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

# 남색 배경 + 흰색 텍스트 + 버튼 스타일
st.markdown(
    """
    <style>
        html, body, [class*="css"], .stApp {
            background-color:#001F3F;
        }
        h1, h2, h3, h4, h5, h6, .stMetricValue, .stMetricLabel {
            color:white;
        }
        .stButton>button {
            background-color:#005F99 !important;
            color:white !important;
            border:none;
            border-radius:6px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌃 남색 테마 대기질 대시보드")
st.markdown("데이터 파일이 필요합니다. 실제 앱에서는 데이터 로딩 후 시각화가 실행됩니다.")
