import streamlit as st
import pandas as pd
import os
import folium
from streamlit.components.v1 import html

# 🌤️ Page config with sky‑blue accent
st.set_page_config(
    page_title="Korea City Air Quality Dashboard",
    page_icon=":sunny:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# inject sky-blue styling
st.markdown(
    """
    <style>
        html, body, [class*="css"], .stApp {
            background-color:#E6F0FF;              /* sky-blue background */
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

@st.cache_data
def load_data():
    pollutant_files = {
        "PM2.5 (㎍/m³)": "미세먼지_PM2.5__월별_도시별_대기오염도_20250610151935.csv",
        "PM10 (㎍/m³)": "미세먼지_PM10__월별_도시별_대기오염도_20250610152841.csv",
        "SO₂ (ppm)": "아황산가스_월별_도시별_대기오염도_20250610152914.csv",
        "NO₂ (ppm)": "이산화질소_월별_도시별_대기오염도_20250610153008.csv",
        "CO (ppm)": "일산화탄소_월별_도시별_대기오염도_20250610153041.csv",
    }

    frames = []
    for pollutant, file in pollutant_files.items():
        if not os.path.exists(file):
            st.error(f"❌ 파일을 찾을 수 없습니다: {file}")
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

    if not frames:
        st.stop()
    return pd.concat(frames, ignore_index=True)

def pollutant_relative_score(city_avg: dict, national_avg: dict) -> dict:
    scores = {}
    for pol, val in city_avg.items():
        base = national_avg.get(pol, 1e-5)
        if pd.isna(val) or pd.isna(base):
            scores[pol] = 50
            continue
        ratio = (base - val) / base
        score = 50 + ratio * 50
        scores[pol] = max(0, min(100, score))
    return scores

def overall_score(subscores: dict) -> float:
    return sum(subscores.values()) / len(subscores)

all_data = load_data()

# sidebar
st.sidebar.header("🔍 조회 조건")
province_list = sorted(all_data["구분(1)"].unique())
selected_province = st.sidebar.selectbox("1️⃣ 시·도 선택", province_list)
city_list = sorted(all_data[all_data["구분(1)"] == selected_province]["구분(2)"].unique())
selected_city = st.sidebar.selectbox("2️⃣ 도시 선택", city_list)
pollutant_options = sorted(all_data["pollutant"].unique())
selected_pollutants = st.sidebar.multiselect(
    "3️⃣ 대기 오염 물질 선택", pollutant_options, default=pollutant_options
)

filtered = all_data[(all_data["구분(1)"] == selected_province) &
                    (all_data["구분(2)"] == selected_city) &
                    (all_data["pollutant"].isin(selected_pollutants))]

st.markdown(f"# 🏙️ {selected_province} {selected_city} 대기질 대시보드")

if filtered.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

# 평균 점수 계산
global_avg = all_data[all_data["month"] == all_data["month"].max()]
national_avg_by_pollutant = global_avg.groupby("pollutant")["value"].mean().to_dict()

avg_values = filtered.groupby("pollutant")["value"].mean().to_dict()
subscores = pollutant_relative_score(avg_values, national_avg_by_pollutant)
final_score = overall_score(subscores)

if final_score >= 80:
    score_tag = "🟢 매우 좋음"
elif final_score >= 60:
    score_tag = "🟡 보통"
elif final_score >= 40:
    score_tag = "🟠 나쁨"
else:
    score_tag = "🔴 매우 나쁨"

st.markdown("### 🧮 종합 대기질 점수")
st.metric(label=f"{score_tag} (100점 만점 기준)", value=f"{final_score:.1f}점")

# latest month metrics
latest_month = filtered["month"].max()
latest_data = filtered[filtered["month"] == latest_month]
metric_cols = st.columns(len(selected_pollutants))
for i, pol in enumerate(selected_pollutants):
    val_series = latest_data[latest_data["pollutant"] == pol]["value"]
    if not val_series.empty:
        metric_cols[i].metric(label=f"{pol} ({latest_month.strftime('%Y-%m')})",
                              value=f"{val_series.iloc[0]:.1f}")

@st.cache_data
def compute_city_scores(df: pd.DataFrame, target_month: pd.Timestamp) -> pd.DataFrame:
    latest_df = df[df["month"] == target_month]
    records = []
    for city, group in latest_df.groupby("구분(1)"):
        avg_dict = group.groupby("pollutant")["value"].mean().to_dict()
        subs = pollutant_relative_score(avg_dict, national_avg_by_pollutant)
        rec = {"city": city, "score": overall_score(subs)}
        records.append(rec)
    return pd.DataFrame(records)

all_latest_month = all_data["month"].max()
city_scores_df = compute_city_scores(all_data, all_latest_month)

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
            emoji = "🟢"
        elif score >= 60:
            color = "yellow"
            emoji = "🟡"
        elif score >= 40:
            color = "orange"
            emoji = "🟠"
        else:
            color = "red"
            emoji = "🔴"
        folium.CircleMarker(
            location=lat_lng,
            radius=12 if city == selected_province else 8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=f"{emoji} {city} : {score:.1f}점",
        ).add_to(m)
    return m

st.markdown("## 🗺️ 전국 대기질 현황 (최신 월)")
korea_map = make_korea_map(city_scores_df)
html(korea_map._repr_html_(), height=600, scrolling=False)

st.markdown("## 📈 월별 추이")
for pol in selected_pollutants:
    pol_df = filtered[filtered["pollutant"] == pol].sort_values("month")
    st.subheader(pol)
    st.line_chart(pol_df.set_index("month")["value"], use_container_width=True)

with st.expander("📋 원본 데이터 보기"):
    table = (
        filtered.pivot_table(index="month", columns="pollutant", values="value")
        .round(1)
        .reset_index()
    )
    table["month"] = table["month"].dt.strftime("%Y-%m")
    st.dataframe(table, use_container_width=True)

st.caption("데이터 출처: 환경부 공개 API — 2024년 월별 측정값")
