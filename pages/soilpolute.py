@st.cache_data
def load_data():
    try:
        df = pd.read_csv(
            "토양오염실태조사결과_조사기관별_오염도_20250617151231.csv",
            header=[0, 1],
            skiprows=[2],
            encoding='utf-8'
        )

        # 컬럼 정리
        df.columns = [f"{col[0]} ({col[1]})" if col[1] != '소계' else col[0] for col in df.columns]
        df.rename(columns={"구분(1) (구분(1))": "시도", "구분(2) (구분(2))": "기관"}, inplace=True)

        # 사용할 오염물질 컬럼 정의
        selected_cols = [
            "2023 (카드뮴 Cd (mg/kg))", "2023 (납 Pb (mg/kg))", "2023 (수은 Hg (mg/kg))",
            "2023 (유류 (mg/kg))", "2023 (유류 (mg/kg).1)", "2023 (유류 (mg/kg).4)",
            "2023 (수소이온농도 pH (pH))"
        ]

        # 필요한 컬럼만 선택
        df = df[["시도", "기관"] + selected_cols]

        # ✅ "계" 제거
        df = df[df["시도"] != "계"]

        # 숫자형 변환
        df[selected_cols] = df[selected_cols].apply(pd.to_numeric, errors="coerce")

        return df

    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류 발생: {e}")
        return pd.DataFrame()
