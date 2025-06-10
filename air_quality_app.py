import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Korea City Air Quality Dashboard", layout="wide")

@st.cache_data
def load_data():
    """Load and tidy all pollutant CSV files into one long-format DataFrame."""
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

        # '총계' 행 제거 및 숫자형 변환
        df = df[df["구분(1)"] != "총계"].copy()
        month_cols = [col for col in df.columns if col.startswith("2024.")]
        df[month_cols] = df[month_cols].apply(pd.to_numeric, errors="coerce")

        # long format 변환
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

# 데이터 로드
all_data = load_data()

# 사이드바 UI
st.sidebar.header("🔍 조회 조건")
province_list = sorted(all_data["구분(1)"].unique())
selected_province = st.sidebar.selectbox("1️⃣ 시·도 선택", province_list)

city_list = sorted(all_data[all_data["구분(1)"] == selected_province]["구분(2)"].unique())
selected_city = st.sidebar.selectbox("2️⃣ 도시 선택", city_list)

pollutant_options = sorted(all_data["pollutant"].unique())
selected_pollutants = st.sidebar.multiselect(
    "3️⃣ 대기 오염 물질 선택",
    pollutant_options,
    default=pollutant_options,
)

# 데이터 필터링
filtered = all_data[(all_data["구분(1)"] == selected_province) &
                    (all_data["구분(2)"] == selected_city) &
                    (all_data["pollutant"].isin(selected_pollutants))]

st.title(f"🏙️ {selected_province} {selected_city} 대기질 대시보드")

if filtered.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

# ✅ 대기질 점수 계산 및 표시
score_data = filtered.groupby("pollutant")["value"].mean()

normalized_scores = {
    "PM2.5 (㎍/m³)": max(0, 100 - score_data.get("PM2.5 (㎍/m³)", 0) * 2),
    "PM10 (㎍/m³)": max(0, 100 - score_data.get("PM10 (㎍/m³)", 0) * 1.5),
    "SO₂ (ppm)": max(0, 100 - score_data.get("SO₂ (ppm)", 0) * 500),
    "NO₂ (ppm)": max(0, 100 - score_data.get("NO₂ (ppm)", 0) * 300),
    "CO (ppm)": max(0, 100 - score_data.get("CO (ppm)", 0) * 10),
}

final_score = sum(normalized_scores.values()) / len(normalized_scores)

# 시각적 색상 및 이모지 매핑
if final_score >= 80:
    score_color = "🟢 매우 좋음"
elif final_score >= 60:
    score_color = "🟡 보통"
elif final_score >= 40:
    score_color = "🟠 나쁨"
else:
    score_color = "🔴 매우 나쁨"

st.markdown("""
### 🧮 종합 대기질 점수
""")
st.metric(label=f"{score_color} (100점 만점 기준)", value=f"{final_score:.1f}점")

# 최신 월(가장 최근 데이터) 메트릭 표시
latest_month = filtered["month"].max()
latest_data = filtered[filtered["month"] == latest_month]

metric_cols = st.columns(len(selected_pollutants))
for i, pol in enumerate(selected_pollutants):
    val_series = latest_data[latest_data["pollutant"] == pol]["value"]
    if not val_series.empty:
        metric_cols[i].metric(label=f"{pol} ({latest_month.strftime('%Y-%m')})",
                              value=f"{val_series.iloc[0]:.1f}")

# 라인 차트 출력
for pol in selected_pollutants:
    pol_df = filtered[filtered["pollutant"] == pol].sort_values("month")
    st.subheader(pol)
    st.line_chart(pol_df.set_index("month")["value"], use_container_width=True)

# 데이터 테이블
with st.expander("📋 원본 데이터 보기"):
    table = (
        filtered.pivot_table(index="month",
                              columns="pollutant",
                              values="value")
        .round(1)
        .reset_index()
    )
    table["month"] = table["month"].dt.strftime("%Y-%m")
    st.dataframe(table, use_container_width=True)

# 주석
st.caption("데이터 출처: 환경부 공개 API (2024년 월별 측정값)")
