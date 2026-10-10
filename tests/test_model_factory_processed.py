from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.model_factory import create_models

ROOT = Path(__file__).resolve().parents[1]


def tables():
    stops = pd.read_csv(ROOT / 'data' / 'processed' / 'bus_stops.csv', encoding='utf-8-sig',
                        dtype={'stop_id': str, 'district_code': str})
    districts = gpd.read_file(ROOT / 'data' / 'processed' / 'districts.geojson')
    return stops, districts


def test_actual_data():
    stops, districts = tables()
    objects, areas = create_models(stops, districts)
    assert len(objects) == len(stops) == 11215
    assert len(areas) == len(districts) == 25
    assert objects[0].stop_id == stops.iloc[0]['stop_id']
    assert objects[0].get_location() == (stops.iloc[0]['latitude'], stops.iloc[0]['longitude'])
    assert objects[0].get_district() == areas[objects[0].district_code].district_name
    assert all(d.population is None for d in areas.values())


@pytest.mark.parametrize('modify', ['unknown_code', 'wrong_name', 'duplicate_stop', 'wrong_count', 'missing_column', 'numeric_id'])
def test_invalid_input(modify):
    stops, districts = tables()
    if modify == 'unknown_code':
        stops.loc[0, 'district_code'] = '99999'
    elif modify == 'wrong_name':
        stops.loc[0, 'district_name'] = '다른구'
    elif modify == 'duplicate_stop':
        stops.loc[1, 'stop_id'] = stops.loc[0, 'stop_id']
    elif modify == 'wrong_count':
        districts.loc[0, 'bus_stop_count'] += 1
    elif modify == 'missing_column':
        stops = stops.drop(columns='district_code')
    elif modify == 'numeric_id':
        stops['stop_id'] = stops['stop_id'].astype(object)
        stops.loc[0, 'stop_id'] = 1001
    with pytest.raises(ValueError):
        create_models(stops, districts)
