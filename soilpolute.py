import streamlit as st
import pandas as pd
import folium
from streamlit.components.v1 import html
import numpy as np

# 페이지 설정
st.set_page_config(page_title="토양오염 실태 지도", layout="wide")

st.title("🧪 대한민국 토양오염 실태 지도 (2023)")
st.caption("출처: 환경부 공개자료 - 토양오염실태조사")

# 데이터 불러오기
@st.cache_data
def load_data():
    df = pd.read_csv("토양오염실태조사결과_조사기관별_오염도_20250617151231.csv", header=[0, 1], skiprows=[2], encoding='utf-8')
    df.columns = [f"{col[0]} ({col[1]})" if col[1] != '소계' else col[0] for col in df.columns]
    df.rename(columns={"구분(1) (구분(1))": "시도", "구분(2) (구분(2))": "기관"}, inplace=True)
    
    # 주요 오염물질 선택
    selected_cols = [
        "2023 (카드뮴 Cd (mg/kg))", "2023 (납 Pb (mg/kg))", "2023 (수은 Hg (mg/kg))",
        "2023 (유류 (mg/kg))", "2023 (유류 (mg/kg).1)", "2023 (유류 (mg/kg).4)",
        "2023 (수소이온농도 pH (pH))"
    ]
    df = df[["시도", "기관"] + selected_cols]
    df[selected_cols] = df[selected_cols].apply(pd.to_numeric, errors="coerce")
    
    return df

data = load_data()

# 시도별 평균값 계산
mean_by_city = data.groupby("시도").mean(numeric_only=True).reset_index()

# 좌표 설정
CITY_COORDS = {
    "서울특별시": (37.5665, 126.9780),
    "부산광역시": (35.1796, 129.0756),
    "대구광역시": (35.8714, 128.6014),
    "인천광역시": (37.4563, 126.7052),
    "광주광역시": (35.1595, 126.8526),
    "대전광역시": (36.3504, 127.3845),
    "울산광역시": (35.5384, 129.3114),
    "세종특별자치시": (36.4801, 127.2890),
    "경기도": (37.2636, 127.0286),
    "강원특별자치도": (37.8228, 128.1555),
    "충청북도": (36.6357, 127.4917),
    "충청남도": (36.5184, 126.8000),
    "전북특별자치도": (35.8200, 127.1088),
    "전라남도": (34.8161, 126.4635),
    "경상북도": (36.4919, 128.8889),
    "경상남도": (35.4606, 128.2132),
    "제주특별자치도": (33.4996, 126.5312)
}

# 지도 생성 함수
def make_map(df):
    m = folium.Map(location=[36.5, 127.8], zoom_start=7)
    for _, row in df.iterrows():
        city = row["시도"]
        coords = CITY_COORDS.get(city)
        if coords:
            cd = row["2023 (카드뮴 Cd (mg/kg))"]
            pb = row["2023 (납 Pb (mg/kg))"]
            hg = row["2023 (수은 Hg (mg/kg))"]
            tph = row["2023 (유류 (mg/kg).4)"]
            ph = row["2023 (수소이온농도 pH (pH))"]
            label = (
                f"<b>{city}</b><br>"
                f"카드뮴: {cd:.2f} mg/kg<br>"
                f"납: {pb:.2f} mg/kg<br>"
                f"수은: {hg:.2f} mg/kg<br>"
                f"유류(TPH): {tph:.2f} mg/kg<br>"
                f"pH: {ph:.2f}"
            )
            folium.CircleMarker(
                location=coords,
                radius=10,
                color="crimson",
                fill=True,
                fill_color="crimson",
                fill_opacity=0.7,
                popup=folium.Popup(label, max_width=300)
            ).add_to(m)
    return m

# 지도 표시
st.markdown("### 🗺️ 시도별 토양오염 평균 지도")
map_obj = make_map(mean_by_city)
html(map_obj._repr_html_(), height=600)

# 데이터 테이블
st.markdown("### 📋 시도별 오염물질 평균 농도 (단위: mg/kg 또는 pH)")
st.dataframe(mean_by_city.set_index("시도").round(3), use_container_width=True)
