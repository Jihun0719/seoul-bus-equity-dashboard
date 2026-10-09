"""전처리된 표를 BusStop 및 District 객체로 변환한다.

파일 읽기·정제·좌표 기반 자치구 판별은 DataLoader의 책임이다.
이 모듈은 객체 생성과 두 결과 표 사이의 연결 무결성만 검사한다.
"""

import pandas as pd
import geopandas as gpd

from models.bus_stop import BusStop
from models.district import District


STOP_COLUMNS = (
    "stop_id", "stop_name", "longitude", "latitude",
    "district_code", "district_name",
)
DISTRICT_COLUMNS = (
    "district_code", "district_name", "geometry", "area_km2",
    "living_population", "bus_stop_count",
)


def _require_columns(table, required, label):
    missing = [name for name in required if name not in table.columns]
    if missing:
        raise ValueError(f"{label}에 필요한 열이 없습니다: {missing}")


def _check_identifier(value, label):
    # 코드와 ID는 유효한 숫자라도 문자열로 유지해야 앞자리 0이 사라지지 않는다.
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}는 비어 있지 않은 문자열이어야 합니다. 문자열 dtype을 확인하세요.")
    return value


def create_models(stops_data: pd.DataFrame, districts_data: gpd.GeoDataFrame):
    """전처리 결과를 (list[BusStop], dict[str, District])로 변환한다.

    `districts_data`의 키는 district_code이며, 정류장 객체의 코드로 조회한다.
    원본 표는 변경하지 않는다. 불일치는 보정하지 않고 ValueError를 발생시킨다.
    """
    if not isinstance(stops_data, pd.DataFrame):
        raise TypeError("stops_data는 pandas.DataFrame이어야 합니다.")
    if not isinstance(districts_data, gpd.GeoDataFrame):
        raise TypeError("districts_data는 geopandas.GeoDataFrame이어야 합니다.")

    _require_columns(stops_data, STOP_COLUMNS, "정류장 표")
    _require_columns(districts_data, DISTRICT_COLUMNS, "자치구 표")

    district_models: dict[str, District] = {}
    for row in districts_data.itertuples(index=False):
        code = _check_identifier(row.district_code, "자치구 코드")
        if code in district_models:
            raise ValueError(f"자치구 코드가 중복됩니다: {code}")
        district_models[code] = District(
            district_name=row.district_name,
            area=row.area_km2,
            population=None,  # 현재 전처리 결과에는 등록인구 열이 없음
            living_population=row.living_population,
            bus_stop_count=row.bus_stop_count,
            district_code=code,
            geometry=row.geometry,
            population_date=(row.population_date if "population_date" in districts_data.columns else ""),
        )

    bus_stop_models: list[BusStop] = []
    seen_ids: set[str] = set()
    counts = {code: 0 for code in district_models}
    for row in stops_data.itertuples(index=False):
        stop_id = _check_identifier(row.stop_id, "정류장 ID")
        code = _check_identifier(row.district_code, "정류장 소속 자치구 코드")
        if stop_id in seen_ids:
            raise ValueError(f"정류장 ID가 중복됩니다: {stop_id}")
        seen_ids.add(stop_id)
        district = district_models.get(code)
        if district is None:
            raise ValueError(f"정류장 {stop_id}의 자치구 코드가 존재하지 않습니다: {code}")
        if row.district_name != district.district_name:
            raise ValueError(
                f"정류장 {stop_id}의 자치구 이름이 일치하지 않습니다: "
                f"{row.district_name!r} != {district.district_name!r}"
            )
        bus_stop_models.append(BusStop(
            stop_id=stop_id,
            latitude=row.latitude,
            longitude=row.longitude,
            district=row.district_name,
            stop_name=row.stop_name,
            district_code=code,
        ))
        counts[code] += 1

    for code, district in district_models.items():
        if counts[code] != district.bus_stop_count:
            raise ValueError(
                f"{district.district_name}({code}) 정류장 수 불일치: "
                f"객체 {counts[code]}개, 자치구 요약 {district.bus_stop_count}개"
            )

    return bus_stop_models, district_models
