import streamlit as st
import pandas as pd
import os
import folium
from streamlit.components.v1 import html
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Korea City Air Quality Dashboard",
    page_icon=":sunny:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        html, body, [class*="css"], .stApp {
            background-color:#F0F8FF;
        }
        h1, h2, h3, h4, h5, h6, .stMetricValue, .stMetricLabel {
            color:#1E90FF;
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

@st.cache_data
def load_data():
    pollutant_files = {
        "PM2.5 (㎍/m³)": "미세먼지_PM2.5.csv",
        "PM10 (㎍/m³)": "미세먼지_PM10.csv",
        "SO₂ (ppm)": "SO2.csv",
        "NO₂ (ppm)": "NO2.csv",
        "CO (ppm)": "CO.csv",
    }

    frames = []
    for pollutant, file in pollutant_files.items():
        if not os.path.exists(file):
            st.error(f"❌ 파일 없음: {file}")
            continue

        df = pd.read_csv(file, encoding="utf-8-sig")
        df = df[df["구분(1)"] != "총계"].copy()
        month_cols = [col for col in df.columns if col.startswith("2024.")]
        df[month_cols] = df[month_cols].apply(pd.to_numeric, errors="coerce")

        df_long = df.melt(id_vars=["구분(1)", "구분(2)"],
                           value_vars=month_cols,
                           var_name="month",
                           value_name="value")
        df_long["pollutant"] = pollutant
        df_long["month"] = pd.to_datetime(df_long["month"], format="%Y.%m")
        frames.append(df_long)

    return pd.concat(frames, ignore_index=True)

all_data = load_data()

# Sidebar
st.sidebar.header("🔍 조회 조건")
province_list = sorted(all_data["구분(1)"].unique())
selected_province = st.sidebar.selectbox("1️⃣ 시·도 선택", province_list)
city_list = sorted(all_data[all_data["구분(1)"] == selected_province]["구분(2)"].unique())
selected_city = st.sidebar.selectbox("2️⃣ 도시 선택", city_list)

pollutant_options = sorted(all_data["pollutant"].unique())
selected_pollutants = st.sidebar.multiselect("3️⃣ 대기 오염 물질 선택", pollutant_options, default=pollutant_options)

# 필터링
filtered = all_data[(all_data["구분(1)"] == selected_province) &
                    (all_data["구분(2)"] == selected_city) &
                    (all_data["pollutant"].isin(selected_pollutants))]

st.markdown(f"# :cityscape: {selected_province} {selected_city} 대기질 대시보드")

if filtered.empty:
    st.warning("조건에 해당하는 데이터가 없습니다.")
    st.stop()

latest_global = all_data[all_data["month"] == all_data["month"].max()]
global_avg_by_pollutant = latest_global.groupby("pollutant")["value"].mean().to_dict()

def pollutant_relative_score(avg_dict: dict, baseline: dict) -> dict:
    scores = {}
    for pol, val in avg_dict.items():
        base = baseline.get(pol, 1e-5)
        if pd.isna(val):
            scores[pol] = 50
            continue
        diff_ratio = (base - val) / base
        score = 50 + diff_ratio * 50
        scores[pol] = min(max(score, 0), 100)
    return scores

def overall_score(subscores: dict) -> float:
    return sum(subscores.values()) / len(subscores)

avg_values = filtered.groupby("pollutant")["value"].mean().to_dict()
subscores = pollutant_relative_score(avg_values, global_avg_by_pollutant)
final_score = overall_score(subscores)

if final_score >= 80:
    score_tag = ":green_circle: 매우 좋음"
elif final_score >= 60:
    score_tag = ":yellow_circle: 보통"
elif final_score >= 40:
    score_tag = ":orange_circle: 나쁨"
else:
    score_tag = ":red_circle: 매우 나쁨"

st.markdown("""### 🧮 종합 대기질 점수""")
st.metric(label=f"{score_tag} (기준 50점)", value=f"{final_score:.1f}점")

# 최신 월 데이터
latest_month = filtered["month"].max()
latest_data = filtered[filtered["month"] == latest_month]
metric_cols = st.columns(len(selected_pollutants))
for i, pol in enumerate(selected_pollutants):
    val_series = latest_data[latest_data["pollutant"] == pol]["value"]
    if not val_series.empty:
        metric_cols[i].metric(label=f"{pol} ({latest_month.strftime('%Y-%m')})", value=f"{val_series.iloc[0]:.1f}")

@st.cache_data
def compute_city_scores(df: pd.DataFrame, target_month: pd.Timestamp) -> pd.DataFrame:
    latest_df = df[df["month"] == target_month]
    records = []
    for city, group in latest_df.groupby("구분(1)"):
        avg_dict = group.groupby("pollutant")["value"].mean().to_dict()
        subs = pollutant_relative_score(avg_dict, global_avg_by_pollutant)
        rec = {"city": city, "score": overall_score(subs)}
        records.append(rec)
    return pd.DataFrame(records)

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
    "제주특별자치도": (33.4996, 126.5312),
}

def make_korea_map(df: pd.DataFrame) -> folium.Map:
    m = folium.Map(location=[36.5, 127.8], zoom_start=7, tiles="CartoDB positron")
    for _, row in df.iterrows():
        city = row["city"]
        score = row["score"]
        lat_lng = CITY_COORDS.get(city)
        if not lat_lng:
            continue
        if score >= 80:
            color = "green"
        elif score >= 60:
            color = "yellow"
        elif score >= 40:
            color = "orange"
        else:
            color = "red"

        folium.CircleMarker(
            location=lat_lng,
            radius=12 if city == selected_province else 8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=f"{city} : {score:.1f}점",
        ).add_to(m)
    return m

city_scores_df = compute_city_scores(all_data, all_data["month"].max())
st.markdown("## :map: 전국 대기질 현황 (최신 월)")
html(make_korea_map(city_scores_df)._repr_html_(), height=600, scrolling=False)

st.markdown("## :chart_with_upwards_trend: 월별 추이 및 시간 변화")
for pol in selected_pollutants:
    pol_df = filtered[filtered["pollutant"] == pol].sort_values("month")
    st.subheader(pol)
    fig, ax = plt.subplots()
    ax.plot(pol_df["month"], pol_df["value"], marker='o')
    ax.set_title(f"{selected_province} {selected_city} - {pol}")
    ax.set_ylabel("측정값")
    ax.grid(True)
    st.pyplot(fig)

with st.expander("📋 원본 데이터 보기"):
    table = filtered.pivot_table(index="month", columns="pollutant", values="value").round(1).reset_index()
    table["month"] = table["month"].dt.strftime("%Y-%m")
    st.dataframe(table, use_container_width=True)

st.caption("데이터 출처: 환경부 공개 API — 2024년 월별 측정값")
