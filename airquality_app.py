import streamlit as st
import pandas as pd
import os
import folium
import branca.colormap as cm
from streamlit.components.v1 import html

st.set_page_config(
    page_title="Air Quality Dashboard",
    page_icon=":sunny:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    html, body, .stApp {
        background-color: #E6F0FA;
        color: white;
    }
    h1, h2, h3, h4, h5, h6, .stMetricValue, .stMetricLabel {
        color: white;
    }
    .stButton>button {
        background-color:#1E90FF !important;
        color:white !important;
    }
</style>
""", unsafe_allow_html=True)

# 언어 선택
lang = st.sidebar.selectbox("🌐 Language / 언어", ["한국어", "English"])

LABELS = {
    "한국어": {
        "title": "대한민국 대기질 대시보드",
        "province": "1️⃣ 시·도 선택",
        "city": "2️⃣ 도시 선택",
        "pollutants": "3️⃣ 대기 오염 물질 선택",
        "score": "🧮 종합 대기질 점수",
        "national_map": "🗺️ 전국 대기질 지도 (최신 월)",
        "national_avg": "📊 월별 전국 평균 오염도",
        "detail": "📍 상세 정보",
        "no_data": "선택한 조건에 해당하는 데이터가 없습니다.",
    },
    "English": {
        "title": "Korea Air Quality Dashboard",
        "province": "1️⃣ Select Province",
        "city": "2️⃣ Select City",
        "pollutants": "3️⃣ Select Pollutants",
        "score": "🧮 Overall Air Quality Score",
        "national_map": "🗺️ Nationwide Air Quality Map",
        "national_avg": "📊 Monthly National Average Pollutants",
        "detail": "📍 Detailed View",
        "no_data": "No data for the selected conditions.",
    },
}
L = LABELS[lang]

# 데이터 불러오기
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
    for pol, file in pollutant_files.items():
        if not os.path.exists(file):
            st.error(f"❌ Missing file: {file}")
            continue
        df = pd.read_csv(file, encoding="utf-8-sig")
        df = df[df["구분(1)"] != "총계"]
        month_cols = [col for col in df.columns if col.startswith("2024.")]
        df[month_cols] = df[month_cols].apply(pd.to_numeric, errors="coerce")
        df_long = df.melt(id_vars=["구분(1)", "구분(2)"],
                          value_vars=month_cols,
                          var_name="month",
                          value_name="value")
        df_long["pollutant"] = pol
        df_long["month"] = pd.to_datetime(df_long["month"], format="%Y.%m")
        frames.append(df_long)
    return pd.concat(frames, ignore_index=True)
all_data = load_data()
pollutant_options = sorted(all_data["pollutant"].unique())
latest_month = all_data["month"].max()

# 점수 계산
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

# 도시 점수 계산
@st.cache_data
def compute_city_scores(df: pd.DataFrame, month: pd.Timestamp) -> pd.DataFrame:
    base = df[df["month"] == month]
    national_avg = base.groupby("pollutant")["value"].mean().to_dict()
    records = []
    for city, group in base.groupby("구분(1)"):
        avg_dict = group.groupby("pollutant")["value"].mean().to_dict()
        subs = pollutant_relative_score(avg_dict, national_avg)
        records.append({"city": city, "score": overall_score(subs)})
    return pd.DataFrame(records), national_avg

city_scores_df, national_avg_by_pollutant = compute_city_scores(all_data, latest_month)

# 좌표
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

# folium 지도 생성 함수
def make_korea_map(df: pd.DataFrame, focus_city=None) -> folium.Map:
    m = folium.Map(location=[36.5, 127.8], zoom_start=7, tiles="CartoDB positron")
    colormap = cm.linear.YlGnBu_09.scale(0, 100)
    colormap.caption = 'Air Quality Score'
    colormap.add_to(m)

    for _, row in df.iterrows():
        city, score = row["city"], row["score"]
        coords = CITY_COORDS.get(city)
        if not coords:
            continue
        folium.CircleMarker(
            location=coords,
            radius=10 + score / 15,
            color=colormap(score),
            fill=True,
            fill_color=colormap(score),
            fill_opacity=0.9,
            tooltip=f"{city}: {score:.1f}점",
        ).add_to(m)

    if focus_city and CITY_COORDS.get(focus_city):
        m.location = CITY_COORDS[focus_city]
        m.zoom_start = 10

    return m
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
    
def make_korea_map(df: pd.DataFrame, focus_city: str = None) -> folium.Map:
    m = folium.Map(location=[36.5, 127.8], zoom_start=7, tiles="CartoDB positron")
    colormap = cm.linear.YlGnBu_09.scale(0, 100)
    colormap.caption = "Air Quality Score"
    for _, row in df.iterrows():
        city = row["city"]
        score = row["score"]
        latlng = CITY_COORDS.get(city)
        if latlng:
            folium.CircleMarker(
                location=latlng,
                radius=10 + score / 15,
                color=colormap(score),
                fill=True,
                fill_color=colormap(score),
                fill_opacity=0.9,
                tooltip=f"{city} : {score:.1f}",
            ).add_to(m)
    colormap.add_to(m)
    return m
st.title(f"🏙️ {L['title']}")

# --- 사용자 입력 ---
province_list = sorted(all_data["구분(1)"].unique())
selected_province = st.sidebar.selectbox(L["province"], [""] + province_list)

if selected_province:
    city_list = sorted(all_data[all_data["구분(1)"] == selected_province]["구분(2)"].unique())
    selected_city = st.sidebar.selectbox(L["city"], [""] + city_list)
else:
    selected_city = ""

selected_pollutants = st.sidebar.multiselect(L["pollutants"], pollutant_options, default=pollutant_options)

# --- 조건에 따른 대시보드 ---
if not selected_province or not selected_city:
    # 전국 대시보드
    st.subheader(L["national_map"])
    nat_map = make_korea_map(city_scores_df)
    html(nat_map._repr_html_(), height=600)

    st.subheader(L["national_avg"])
    for pol in pollutant_options:
        df = all_data[all_data["pollutant"] == pol]
        line = df.groupby("month")["value"].mean()
        st.line_chart(line, use_container_width=True)

else:
    # 특정 도시 대시보드
    filtered = all_data[
        (all_data["구분(1)"] == selected_province) &
        (all_data["구분(2)"] == selected_city) &
        (all_data["pollutant"].isin(selected_pollutants))
    ]
    st.header(f"📍 {selected_province} {selected_city} {L['detail']}")
    
    if filtered.empty:
        st.warning(L["no_data"])
        st.stop()

    # 점수 계산
    city_avg = filtered.groupby("pollutant")["value"].mean().to_dict()
    subscores = pollutant_relative_score(city_avg, national_avg_by_pollutant)
    final_score = overall_score(subscores)

    st.subheader(L["score"])
    st.metric("Score", f"{final_score:.1f} / 100")

    # 확대 지도
    coords = CITY_COORDS.get(selected_province)
    if coords:
        m = folium.Map(location=coords, zoom_start=10)
        folium.Marker(coords, tooltip=f"{selected_city}").add_to(m)
        html(m._repr_html_(), height=500)

    # 추이
    st.subheader("📈 월별 추이")
    for pol in selected_pollutants:
        pol_df = filtered[filtered["pollutant"] == pol].sort_values("month")
        st.line_chart(pol_df.set_index("month")["value"], use_container_width=True)

    with st.expander("📋 원본 데이터"):
        table = (
            filtered.pivot_table(index="month", columns="pollutant", values="value")
            .round(1).reset_index()
        )
        table["month"] = table["month"].dt.strftime("%Y-%m")
        st.dataframe(table, use_container_width=True)

st.caption("데이터 출처: 환경부 공개 API — 2024년 월별 대기오염 측정값")
