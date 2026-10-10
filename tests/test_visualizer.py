"""E 담당 지도 모듈 테스트: Streamlit 실행 없이 검증 가능."""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

from utils.model_factory import create_models
from utils.visualizer import Visualizer

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def visualizer():
    stops = pd.read_csv(ROOT / "data/processed/bus_stops.csv", dtype={"stop_id": str, "district_code": str})
    districts = gpd.read_file(ROOT / "data/processed/districts.geojson")
    _, district_models = create_models(stops, districts)
    stop_models, _ = create_models(stops, districts)
    return Visualizer(district_models, stop_models)


def test_all_districts(visualizer):
    assert len(visualizer.prepare_map_data()) == 25


def test_bus_stop_count(visualizer):
    assert len(visualizer.bus_stops) == 11215


def test_metrics_and_scores(visualizer):
    df = visualizer.prepare_map_data()
    assert df["equity_score"].between(0, 100).all()
    assert (df["stop_density"] > 0).all()
    assert (df["stops_per_population"] > 0).all()


@pytest.mark.parametrize("metric", list(Visualizer.METRICS))
def test_create_map(visualizer, metric):
    fig = visualizer.create_map(metric)
    assert len(fig.data[0].locations) == 25
    assert len(fig.data) == 1


def test_bus_stop_layer(visualizer):
    fig = visualizer.create_map(show_bus_stops=True)
    assert len(fig.data) == 2
    assert len(fig.data[1].lat) == 11215


def test_unknown_metric(visualizer):
    with pytest.raises(ValueError):
        visualizer.create_map("invalid")


def test_selected_district_shows_only_its_stops(visualizer):
    fig = visualizer.create_map(selected_district_code="11320", show_bus_stops=True)
    expected = sum(s.district_code == "11320" for s in visualizer.bus_stops)
    assert len(fig.data) == 2
    assert len(fig.data[1].lat) == expected
    assert expected > 0
    assert fig.layout.geo.lonaxis.range is not None
    assert fig.layout.geo.lataxis.range is not None


def test_invalid_district_code(visualizer):
    with pytest.raises(ValueError):
        visualizer.create_map(selected_district_code="00000")
