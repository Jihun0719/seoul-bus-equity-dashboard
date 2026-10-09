"""개별 버스정류소를 표현하는 데이터 모델.

README 필수 인터페이스: stop_id, latitude, longitude, district,
get_location(), get_district().
"""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class BusStop:
    """정류소 한 곳의 전처리된 기본 정보를 보관하는 읽기 전용 객체."""

    stop_id: str
    latitude: float
    longitude: float
    district: str
    stop_name: str = ""
    district_code: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.stop_id, str) or not self.stop_id.strip():
            raise ValueError("stop_id는 비어 있지 않은 문자열이어야 합니다.")
        if not isinstance(self.district, str) or not self.district.strip():
            raise ValueError("district는 비어 있지 않은 자치구 이름이어야 합니다.")
        if not isinstance(self.stop_name, str):
            raise ValueError("stop_name은 문자열이어야 합니다.")
        if not isinstance(self.district_code, str):
            raise ValueError("district_code는 문자열이어야 합니다.")
        for name, value, minimum, maximum in (
            ("latitude", self.latitude, -90, 90),
            ("longitude", self.longitude, -180, 180),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name}는 숫자여야 합니다.")
            if not isfinite(value) or not minimum <= value <= maximum:
                raise ValueError(f"{name}는 {minimum}~{maximum} 범위여야 합니다.")

    def get_location(self) -> tuple[float, float]:
        """(위도, 경도) 순서의 튜플을 반환합니다."""
        return (self.latitude, self.longitude)

    def get_district(self) -> str:
        """소속 자치구 이름을 반환합니다."""
        return self.district
