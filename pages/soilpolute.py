import streamlit as st
import pandas as pd
import folium
from streamlit.components.v1 import html
import numpy as np
import branca.colormap as cm
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import streamlit.runtime
from packaging import version

# ──────────────────────────────────────────────
# ✅ Streamlit 버전에 따라 cache 데코레이터 선택
st_version = streamlit.__version__
if version.parse(st_version) >= version.parse("1.18.0"):
    cache_decorator = st.cache_data
else:
    cache_decorator = st.cache

# ──────────────────────────────────────────────
# 페이지 설정
st.set_page_config(page_title="토양오염 실태 지도", layout="wide")

st.title(":test_tube: 대한민국 토양오염 실태 지도 (2023)")
st.caption("출처: 환경부 공개자료 - 토양오염실태조사")

# ──────────────────────────────────────────────
# 데이터 불러오기
@cache_decorator
def load_data():
    try:
        df = pd.read_csv(
            "토양오염실태조사결과_조사기관별_오염도_20250617151231.csv",
            header=[0, 1],
            skiprows=[2],
            encoding='utf-8'
        )
        df.columns = [f"{col[0]} ({col[1]})" if col[1] != '소계' else col[0] for col in df.columns]
        df.rename(columns={"구분(1) (구분(1))": "시도", "구분(2) (구분(2))": "기관"}, inplace=True)

        selected_cols = [
            "2023 (카드뮴 Cd (mg/kg))", "2023 (납 Pb (mg/kg))", "2023 (수은 Hg (mg/kg))",
            "2023 (유류 (mg/kg))", "2023 (유류 (mg/kg).1)", "2023 (유류 (mg/kg).4)",
            "2023 (수소이온농도 pH (pH))"
        ]

        df = df[["시도", "기관"] + selected_cols]

        # ✅ "계" 제거
        df = df[df["시도"] != "계"]

        df[selected_cols] = df[selected_cols].apply(pd.to_numeric, errors="coerce")

        return df
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류 발생: {e}")
        return pd.DataFrame()

# ──────────────────────────────────────────────
data = load_data()
if data.empty:
    st.stop()

mean_by_city = data.groupby("시도").mean(numeric_only=True).reset_index()

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

max_cd = mean_by_city["2023 (카드뮴 Cd (mg/kg))"].max()
colormap = cm.linear.YlOrRd_09.scale(0, max_cd)
colormap.caption = "카드뮴 농도 (mg/kg)"

# ──────────────────────────────────────────────
# 클릭 시 도시 상세 그래프 생성
def generate_city_chart(city):
    city_df = data[data["시도"] == city].groupby("기관").mean(numeric_only=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    city_df[["2023 (카드뮴 Cd (mg/kg))", "2023 (납 Pb (mg/kg))", "2023 (수은 Hg (mg/kg))"]].plot(kind="bar", ax=ax)
    plt.title(f"{city} 주요 중금속 평균치 (기관별)")
    plt.ylabel("mg/kg")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    data_uri = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f'<img src="data:image/png;base64,{data_uri}" width="400"/>'

# ──────────────────────────────────────────────
# 지도 생성 함수
def make_map(df, selected_city=None):
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
                f"pH: {ph:.2f}<br>"
                + generate_city_chart(city)
            )
            folium.CircleMarker(
                location=coords,
                radius=12 if city == selected_city else 8,
                color=colormap(cd),
                fill=True,
                fill_color=colormap(cd),
                fill_opacity=0.8,
                popup=folium.Popup(label, max_width=450)
            ).add_to(m)
    colormap.add_to(m)
    return m

# ──────────────────────────────────────────────
# UI: 시/도 선택 → 개별 도시 or 전체
st.sidebar.header("🔎 도시별 데이터 조회")
states = sorted(mean_by_city["시도"].unique().tolist())
selected = st.sidebar.selectbox("시/도 선택", ["전체 보기"] + states)

if selected != "전체 보기":
    city_data = mean_by_city[mean_by_city["시도"] == selected].copy()
    st.markdown(f"### :world_map: {selected}의 토양오염 평균 지도")
    html(make_map(city_data, selected)._repr_html_(), height=650)
    st.markdown(f"### :bar_chart: {selected}의 오염물질 평균 농도")
    st.dataframe(city_data.set_index("시도").round(3), use_container_width=True)
else:
    st.markdown("### :world_map: 시도별 토양오염 평균 지도")
    html(make_map(mean_by_city)._repr_html_(), height=650)
    st.markdown("### :bar_chart: 시도별 오염물질 평균 농도 (단위: mg/kg 또는 pH)")
    st.dataframe(mean_by_city.set_index("시도").round(3), use_container_width=True)
