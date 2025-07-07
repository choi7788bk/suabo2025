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
            background-color:#E6F2FF;  /* 밝은 하늘색 배경 */
            color:#000000;             /* 기본 텍스트 색상 */
        }
        h1, h2, h3, h4, h5, h6, .stMetricValue, .stMetricLabel {
            color:#000000;             /* 헤더 및 메트릭 텍스트 색상 */
        }
        .stButton>button {
            background-color:#1E90FF !important;
            color:white !important;
            border:none;
            border-radius:6px;
        }
        .css-1v0mbdj, .css-10trblm {  /* sidebar header & markdown 내 텍스트 */
            color:#000000 !important;
        }
        .css-1cpxqw2 { /* metric container background */
            background-color: rgba(255, 255, 255, 0.6) !important;
            border-radius: 10px !important;
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
            emoji = "🟢 매우 좋음"
        elif score >= 60:
            color = "yellow"
            emoji = "🟡 보통"
        elif score >= 40:
            color = "orange"
            emoji = "🟠 나쁨"
        else:
            color = "red"
            emoji = "🔴 매우 나쁨"

        # 선택된 도시 강조
        is_selected = city == selected_province
        radius = 14 if is_selected else 9
        weight = 3 if is_selected else 1
        border_color = "black" if is_selected else color

        folium.CircleMarker(
            location=lat_lng,
            radius=radius,
            color=border_color,
            weight=weight,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(
                html=f"<b>{city}</b><br>{emoji}<br><b>점수:</b> {score:.1f}",
                max_width=200,
            ),
            tooltip=f"{city}: {score:.1f}점",
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

st.markdown("## 🧠 오염물질 설명")

cols = st.columns(3)
cols[0].info("**PM2.5 (초미세먼지)**\n\n폐 깊숙이 침투 → 심혈관질환 및 암 유발")
cols[1].info("**PM10 (미세먼지)**\n\n코·기관지 자극 → 호흡기 악화")
cols[2].info("**NO₂ (이산화질소)**\n\n천식, 기관지염 악화")

cols = st.columns(2)
cols[0].info("**SO₂ (아황산가스)**\n\n점막 자극, 산성비 원인")
cols[1].info("**CO (일산화탄소)**\n\n산소 결합 방해 → 고농도 노출 시 치명적")

# 사이드바에 오염물질 설명 추가
with st.sidebar.expander("📌 오염물질이 건강에 미치는 영향"):
    st.markdown("""
    - **PM2.5 (초미세먼지)**: 폐 깊숙이 침투하여 **호흡기, 심혈관질환**을 유발하며, WHO 지정 **1급 발암물질**입니다.
    - **PM10 (미세먼지)**: 기관지 자극, 천식 및 호흡기 질환 악화.
    - **NO₂ (이산화질소)**: 기관지염, 천식 악화. 자동차 배기가스의 주요 성분.
    - **SO₂ (아황산가스)**: **눈과 점막 자극**, 폐기능 저하, 산성비 유발.
    - **CO (일산화탄소)**: 산소 운반 방해 → 고농도 흡입 시 **두통, 의식 저하, 사망 가능**.
    """)

