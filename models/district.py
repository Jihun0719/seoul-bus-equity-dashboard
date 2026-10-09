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

    #면적당 버스정류장 수 
    def calculate_stop_density(self) -> float:
        """면적 1km²당 버스정류장 수를 계산합니다."""
        return self.bus_stop_count / self.area

    #생할인구당 버스정류장 수
    def calculate_stops_per_population(self) -> float:
        """생활인구 1만 명당 버스정류장 수를 계산합니다."""
        if self.living_population == 0:
            raise ValueError("생활인구가 0이면 계산할 수 없습니다.")

        return self.bus_stop_count / self.living_population * 10000

    #각 변수를 0에서 100 사이로 조정
    @staticmethod
    def normalize(value: float, min_value: float, max_value: float) -> float:
        if min_value > max_value:
            raise ValueError("최솟값은 최댓값보다 클 수 없습니다.")

        if not min_value <= value <= max_value:
            raise ValueError("값은 최솟값과 최댓값 사이에 있어야 합니다.")

        if max_value == min_value:
            return 50.0

        return (value - min_value) / (max_value - min_value) * 100

    

    #상대적인 형평성을 계산(0에서 100 사이)
    def calculate_equity_score(self, density_min: float, density_max: float, population_min: float, population_max: float) -> float:

        density = self.calculate_stop_density()
        population = self.calculate_stops_per_population()

        density_score = self.normalize(density, density_min, density_max)
        population_score = self.normalize(population, population_min, population_max)

        return density_score * 0.5 + population_score * 0.5
    
