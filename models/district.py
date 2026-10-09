"""자치구 기본 정보를 보관하는 모델.

README의 계산 메서드 세 가지는 분석 담당자(D)와 연결할 작업이며,
이 파일은 담당자 C의 기본 정보 관리 범위만 구현합니다.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class District:
    """서울시 자치구 하나의 기초 통계·공간정보를 보관합니다."""

    district_name: str
    area: float
    population: float | None
    living_population: float
    bus_stop_count: int
    district_code: str = ""
    geometry: Any = None
    population_date: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.district_name, str) or not self.district_name.strip():
            raise ValueError("district_name은 비어 있지 않은 문자열이어야 합니다.")
        if not isinstance(self.district_code, str):
            raise ValueError("district_code는 문자열이어야 합니다.")
        if not isinstance(self.population_date, str):
            raise ValueError("population_date는 문자열이어야 합니다.")
        for name, value, permit_none in (
            ("area", self.area, False),
            ("population", self.population, True),
            ("living_population", self.living_population, False),
        ):
            if permit_none and value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name}는 숫자여야 합니다.")
            if not isfinite(value) or value < 0 or (name == "area" and value == 0):
                raise ValueError(f"{name}는 유효한 음이 아닌 값이어야 합니다(면적은 양수).")
        if isinstance(self.bus_stop_count, bool) or not isinstance(self.bus_stop_count, int) or self.bus_stop_count < 0:
            raise ValueError("bus_stop_count는 음이 아닌 정수여야 합니다.")
