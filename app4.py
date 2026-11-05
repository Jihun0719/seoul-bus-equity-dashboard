"""E 담당: 서울시 자치구별 버스 인프라 형평성 Streamlit 대시보드.

실행: python -m streamlit run app.py
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

from utils.model_factory import create_models
from utils.visualizer import Visualizer

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"

st.set_page_config(page_title="서울 버스 인프라 형평성", page_icon="🚌", layout="wide")


@st.cache_resource(show_spinner="정류소 및 자치구 데이터를 불러오는 중...")
def load_dashboard():
    stops_data = pd.read_csv(
        DATA_DIR / "bus_stops.csv",
        encoding="utf-8-sig",
        dtype={"stop_id": str, "district_code": str},
    )
    districts_data = gpd.read_file(DATA_DIR / "districts.geojson")
    districts_data["district_code"] = districts_data["district_code"].astype(str)
    bus_stops, districts = create_models(stops_data, districts_data)
    return Visualizer(districts, bus_stops)


st.title("🚌 서울시 자치구별 버스 인프라 형평성 대시보드")
st.caption("서울시 25개 자치구의 정류소 공급 지표를 비교합니다.")

try:
    visualizer = load_dashboard()
    map_data = visualizer.prepare_map_data()
except (FileNotFoundError, ValueError, KeyError, ImportError) as exc:
    st.error(f"데이터를 불러오지 못했습니다: {exc}")
    st.stop()

population_date = str(map_data["population_date"].iloc[0])
if len(population_date) == 8 and population_date.isdigit():
    population_date = f"{population_date[:4]}-{population_date[4:6]}-{population_date[6:]}"

col1, col2, col3 = st.columns(3)
col1.metric("분석 자치구", f"{len(map_data):,}개")
col2.metric("배정된 버스정류소", f"{len(visualizer.bus_stops):,}개")
col3.metric("생활인구 기준일", population_date or "정보 없음")

st.divider()
metric = st.selectbox(
    "지도에 표시할 지표",
    options=list(Visualizer.METRICS),
    format_func=lambda key: Visualizer.METRICS[key][0],
)

if "selected_district_code" not in st.session_state:
    st.session_state.selected_district_code = None

selected_code = st.session_state.selected_district_code
selected_row = None
if selected_code is not None:
    match = map_data.loc[map_data["district_code"] == selected_code]
    if not match.empty:
        selected_row = match.iloc[0]
    else:
        st.session_state.selected_district_code = None
        selected_code = None

if selected_code is None:
    st.info("지도에서 원하는 자치구를 클릭하면 해당 지역으로 확대되고 버스정류소가 표시됩니다.")
else:
    info_col, reset_col = st.columns([5, 1])
    info_col.success(f"📍 {selected_row['district_name']} 확대 보기 · 버스정류소 {int(selected_row['bus_stop_count']):,}개")
    if reset_col.button("↩ 서울 전체 보기", use_container_width=True):
        st.session_state.selected_district_code = None
        st.rerun()

show_stops = st.checkbox(
    "서울 전체 지도에도 개별 버스정류소 표시 (정류소가 많아 느려질 수 있음)",
    value=False,
)

# Streamlit의 Plotly 선택 이벤트를 받아 클릭한 자치구로 확대합니다.
# Plotly choropleth의 각 영역은 selection.points에 location과 point_index를 제공합니다.
figure = visualizer.create_map(
    metric,
    show_bus_stops=(show_stops or selected_code is not None),
    selected_district_code=selected_code,
)
selection = st.plotly_chart(
    figure,
    use_container_width=True,
    on_select="rerun",
    selection_mode="points",
    key=f"district_map_{metric}_{selected_code or 'all'}",
)
points = selection.selection.points if selection is not None else []
if points:
    clicked = points[0]
    location = clicked.get("location")
    if location is None and clicked.get("curve_number", 0) == 0:
        point_index = clicked.get("point_index")
        if isinstance(point_index, int) and 0 <= point_index < len(map_data):
            location = str(map_data.iloc[point_index]["district_code"])
    if location is not None:
        location = str(location)
        if location != selected_code and location in set(map_data["district_code"]):
            st.session_state.selected_district_code = location
            st.rerun()

st.caption("지도에서 자치구를 클릭해 확대할 수 있습니다. 확대 상태에서는 해당 구의 버스정류소만 빨간 점으로 표시됩니다.")
st.info("종합 형평성 점수는 면적당 정류소 수와 생활인구당 정류소 수를 각각 50% 반영한 상대적 지표입니다. 실제 교통 접근성을 직접 측정한 값은 아닙니다.")

st.subheader("자치구 상세 정보")
if selected_row is None:
    st.caption("지도에서 자치구를 클릭하면 해당 자치구의 상세 정보가 표시됩니다.")
else:
    a, b, c, d = st.columns(4)
    a.metric("정류소", f"{int(selected_row['bus_stop_count']):,}개")
    b.metric("면적당 정류소", f"{selected_row['stop_density']:.2f}개/㎢")
    c.metric("생활인구 1만 명당", f"{selected_row['stops_per_population']:.2f}개")
    d.metric("종합 형평성 점수", f"{selected_row['equity_score']:.1f}점")

st.divider()
st.subheader("추가 분석 (F 담당 연동 예정)")
left, right = st.columns(2)
with left:
    st.markdown("**자치구별 지표 비교 막대그래프**")
    st.caption("F 담당: create_bar_chart() 연결 영역")
with right:
    st.markdown("**생활인구와 정류소 수 산점도**")
    st.caption("F 담당: create_scatter_plot() 연결 영역")
