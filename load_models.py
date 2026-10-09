"""저장된 전처리 결과에서 BusStop/District 객체를 생성하는 실행 예시.

원본(raw) 데이터의 재전처리는 수행하지 않습니다.
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

from utils.model_factory import create_models

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def main():
    stops_data = pd.read_csv(
        PROCESSED_DIR / "bus_stops.csv",
        encoding="utf-8-sig",
        dtype={"stop_id": str, "district_code": str},
    )
    districts_data = gpd.read_file(PROCESSED_DIR / "districts.geojson")
    # GeoJSON을 읽은 뒤에도 코드가 문자열인지 확인한다.
    districts_data["district_code"] = districts_data["district_code"].astype(str)

    bus_stops, districts = create_models(stops_data, districts_data)
    print(f"BusStop 객체 {len(bus_stops)}개, District 객체 {len(districts)}개 생성")
    return bus_stops, districts


if __name__ == "__main__":
    main()
