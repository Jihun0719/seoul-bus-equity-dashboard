# Seoul Bus Infrastructure Equity Dashboard — C 담당 모델링 모듈

> 본 문서는 팀 프로젝트의 기존 `README.md`와 전체 설계도를 보완하는 **담당자 C의 구현 설명서**입니다. 프로젝트 전체 README를 대체하지 않습니다.
>
> **구현 범위:** `BusStop` 클래스 전체, `District` 클래스의 기본 정보 관리, 전처리 데이터의 객체 변환 및 자치구 연결 검증.

## 1. 개요 및 작업 범위

서울시 버스 인프라 형평성 대시보드에서, A·B 담당자가 전처리한 정류장·자치구 데이터를 Python 객체로 표현하여 다른 모듈이 사용할 수 있도록 제공합니다.

- `BusStop`: 개별 버스정류소의 ID, 위치, 소속 자치구 등을 보관하고 조회합니다.
- `District`: 자치구의 기본 정보(이름, 면적, 인구 관련 속성, 정류장 수, 경계 등)를 보관합니다.
- `model_factory`: 전처리 표를 객체로 변환하고 정류장과 자치구 사이의 코드·이름 일치 여부 및 개수 정합성을 검증합니다.
- `load_models.py`: `data/processed/`에 **이미 저장된 전처리 결과**를 읽어 객체 생성 함수를 호출하는 실행 예시입니다.

**담당 범위 밖:** 원본 데이터 전처리, 좌표를 이용한 최초 자치구 배정, 정류장 밀도·인구 대비 정류장 수·형평성 점수 계산, 대시보드 시각화. 좌표 기반 배정은 기존 `DataLoader.assign_districts()`의 결과를 활용하며, C 모듈은 그 배정 결과의 객체 간 정합성을 검증합니다.

## 2. 파일 구성

```text
프로젝트 루트/
├── models/
│   ├── bus_stop.py                    # BusStop 클래스
│   └── district.py                    # District 기본 정보 모델
├── utils/
│   ├── data_loader.py                 # A·B 담당: 기존 전처리 코드
│   └── model_factory.py               # C 담당: 객체 생성·검증 (추가)
├── data/
│   └── processed/
│       ├── bus_stops.csv               # 기존 전처리 정류장 표
│       ├── districts.geojson           # 기존 전처리 자치구 표
│       └── validation_report.json      # A·B 담당 전처리 기록
├── tests/
│   └── test_model_factory_processed.py # C 담당 테스트 (추가)
├── load_models.py                      # C 담당 실행 예시 (추가)
└── README_C.md                         # 본 문서 (추가)
```

기존 설계도에 명시된 모델 파일 외에 `model_factory.py`, `load_models.py`, 테스트 파일 및 본 설명서를 추가했습니다. 기존 `DataLoader`의 전처리 로직은 수정하지 않습니다.

## 3. 입력 데이터

객체 생성에는 **전처리된 두 파일**이 필요합니다.

| 파일 | 필수 열 | 용도 |
|---|---|---|
| `data/processed/bus_stops.csv` | `stop_id`, `stop_name`, `longitude`, `latitude`, `district_code`, `district_name` | 정류장 객체 생성 |
| `data/processed/districts.geojson` | `district_code`, `district_name`, `geometry`, `area_km2`, `living_population`, `bus_stop_count` | 자치구 객체 생성 |

`districts.geojson`에 `population_date` 열이 있으면 함께 사용하며, 없어도 객체를 생성할 수 있습니다.

- **정류장 ID와 자치구 코드는 문자열로 유지**해야 합니다. 예: `stop_id="01001"`의 선행 0을 보존해야 합니다.
- 경도·위도는 WGS84 경위도 기준입니다. `area_km2`는 km² 단위로 이미 계산된 값입니다.
- `living_population`은 특정 날짜의 생활인구로, 주민등록인구와 다릅니다.
- A·B 담당자의 전처리 결과가 이미 준비되어 있으므로 `data/raw/` 재처리는 C 모듈 실행에 필요하지 않습니다.

## 4. 클래스 인터페이스

### 4.1 `BusStop` — `models/bus_stop.py`

`@dataclass(frozen=True)`로 정의되어 생성 후 일반적인 속성 재할당이 제한됩니다.

| 속성 | 타입 | 내용 |
|---|---|---|
| `stop_id` | `str` | 정류소 식별자; 필수 |
| `latitude` | `float` | 위도; 필수, -90~90 범위 |
| `longitude` | `float` | 경도; 필수, -180~180 범위 |
| `district` | `str` | 소속 자치구 **이름**; 필수 |
| `stop_name` | `str` | 정류소 이름; 기본값 `""` |
| `district_code` | `str` | 소속 자치구 **코드**; 기본값 `""` |

**메서드**

- `get_location() -> tuple[float, float]`: **(위도, 경도)** 순서로 반환합니다. GeoPandas의 `points_from_xy()`에서 주로 쓰는 (경도, 위도) 순서와 다르므로 주의해야 합니다.
- `get_district() -> str`: 자치구 **이름**을 반환합니다. `District` 객체 자체나 자치구 코드를 반환하지 않습니다.

생성 시 ID·자치구 이름의 비어 있음, 속성 자료형, 위도·경도 범위 및 NaN/무한대 여부 등을 검사하고 부적절한 값에는 `ValueError`를 발생시킵니다. `district_code`의 실제 존재 여부와 코드-이름 일치 여부는 `model_factory`에서 검사합니다.

### 4.2 `District` — `models/district.py`

`@dataclass(frozen=True)`로 정의된 자치구 기본 정보 모델입니다.

| 속성 | 타입 | 내용 |
|---|---|---|
| `district_name` | `str` | 자치구 이름; 필수 |
| `area` | `float` | 자치구 면적(km²); 필수, 0 초과 |
| `population` | `float \| None` | 주민등록인구; 현재 데이터에서는 `None` |
| `living_population` | `float` | 생활인구; 필수 |
| `bus_stop_count` | `int` | 자치구 내 정류장 수; 필수 |
| `district_code` | `str` | 자치구 연결용 코드; 기본값 `""` |
| `geometry` | `Any` | 자치구 경계 도형; 기본값 `None` |
| `population_date` | `str` | 생활인구 기준일(YYYYMMDD); 기본값 `""` |

생성 직후 문자열 유형, 면적과 인구의 수치 범위, 정류장 수의 정수 여부 등을 검증합니다. 별도의 기본정보 getter를 요구하지 않아 속성을 직접 조회합니다.

**중요:** 기존 팀장 README가 정의한 `calculate_stop_density()`, `calculate_stops_per_population()`, `calculate_equity_score()`는 **담당자 D의 구현 범위이며 현재 이 파일에는 없습니다.** 따라서 C 산출물만으로 해당 메서드를 호출할 수 없습니다.

**등록인구 유의사항:** 현행 전처리 결과에는 주민등록인구 열이 없으므로 `model_factory`는 `population=None`을 명시적으로 전달합니다. `living_population`을 주민등록인구로 대신 사용하지 않습니다. `population` 필드 자체는 생성자에서 생략할 수 없습니다.

## 5. 객체 생성 모듈 — `utils/model_factory.py`

### 입력 및 반환값

```python
from utils.model_factory import create_models

bus_stops, districts = create_models(stops_data, districts_data)
```

- `stops_data`: `pandas.DataFrame` (전처리 정류장 표)
- `districts_data`: `geopandas.GeoDataFrame` (전처리 자치구 표)
- `bus_stops`: `list[BusStop]` — 정류장 객체 목록
- `districts`: `dict[str, District]` — **자치구 코드를 키**로 하는 객체 사전

예를 들어 정류장 객체 `stop`의 소속 자치구 객체는 다음처럼 조회합니다.

```python
stop = bus_stops[0]
district = districts[stop.district_code]

print(stop.get_district())     # 자치구 이름 문자열
print(district.district_name)  # 연결된 District 객체의 이름
print(district.area)           # km² 단위 면적
```

### 처리 및 검증 순서

1. 입력 자료형(`DataFrame`, `GeoDataFrame`)과 필수 열을 확인합니다.
2. 각 자치구 행에서 `District` 객체를 생성하고 `district_code`를 키로 보관합니다.
3. 각 정류장 행에서 `BusStop` 객체를 생성하면서 ID 중복, 자치구 코드의 존재 여부, 코드에 대응하는 자치구 이름 일치 여부를 검증합니다.
4. 생성된 정류장을 코드별로 집계하여 자치구 표의 `bus_stop_count`와 일치하는지 검사합니다.
5. 검증에 성공하면 `(list[BusStop], dict[str, District])`를 반환합니다.

오류를 발견하면 값을 임의로 수정하거나 정류장을 삭제하지 않고 `TypeError` 또는 `ValueError`를 발생시킵니다. **자치구 경계와 좌표의 공간 결합을 다시 수행하지 않습니다.** 입력 DataFrame 자체도 수정하지 않습니다.

## 6. 실행 방법

프로젝트 **최상위 폴더**에서 실행합니다.

### 6.1 실행 환경

- Python 3.10 이상 (`|` 타입 표기 등 사용)
- `pandas`, `geopandas`, `shapely`, `pyogrio`, `pytest` (저장소 `requirements.txt` 참고)

```bash
pip install -r requirements.txt
```

### 6.2 전처리 완료 파일에서 객체 생성

다음 두 파일이 있어야 합니다.

```text
data/processed/bus_stops.csv
data/processed/districts.geojson
```

```bash
python load_models.py
```

`load_models.py`는 두 파일을 읽어 `create_models()`를 호출하며, 생성된 `BusStop`, `District` 객체 수를 출력합니다. **원본 `data/raw/`에서 전처리를 재실행하지 않습니다.** `validation_report.json`은 전처리 기록으로 보존하며 팩토리 입력에는 사용하지 않습니다.

코드에서 직접 객체를 활용할 때는 다음과 같이 사용합니다.

```python
import pandas as pd
import geopandas as gpd
from utils.model_factory import create_models

stops_data = pd.read_csv(
    "data/processed/bus_stops.csv",
    encoding="utf-8-sig",
    dtype={"stop_id": str, "district_code": str},
)
districts_data = gpd.read_file("data/processed/districts.geojson")
districts_data["district_code"] = districts_data["district_code"].astype(str)

bus_stops, districts = create_models(stops_data, districts_data)
```

## 7. 검증 및 테스트

```bash
python -m pytest -q tests/test_model_factory_processed.py
```

2026-10-09 기준 제공된 전처리 결과로 확인한 내용:

- 버스정류장 객체 **11,215개**, 자치구 객체 **25개** 생성
- 정상 데이터 변환 및 조회 확인
- 존재하지 않는 자치구 코드, 코드-이름 불일치, 중복 정류장 ID, 자치구 정류장 수 불일치, 필수 열 누락, 숫자형 정류장 ID의 오류 처리 확인
- **테스트 7개 통과** (실제 데이터 테스트 1개 + 잘못된 입력 6개)

테스트에서 객체 개수 11,215개/25개는 **현재 제공된 전처리 결과를 기준으로 한 기대값**입니다. 다른 시점의 데이터에는 다른 개수가 나올 수 있습니다.

이 검증은 **C 모듈 범위의 테스트**입니다. 전체 대시보드 및 D 담당 분석 메서드와의 최종 통합 테스트가 완료되었다는 의미는 아닙니다.

## 8. 기존 명세 대비 추가 사항 및 유의점

프로젝트의 기존 팀장 README 및 A·B 전처리 명세를 유지하면서, 그곳에 지정되지 않은 사항을 다음과 같이 보완했습니다.

| 구분 | 기존 명세와의 관계 | C 구현 내용 |
|---|---|---|
| `BusStop` 기본 속성·메서드 | 팀장 README에 명시 | `stop_id`, `latitude`, `longitude`, `district`, `get_location()`, `get_district()` 유지 |
| `BusStop` 추가 정보 | 전처리 결과에 존재 | `stop_name`, `district_code` 보관 |
| `District` 추가 정보 | 전처리 결과에 존재 | `district_code`, `geometry`, `population_date` 보관 |
| 객체 변경 제한 | 기존 명세에 미지정 | `@dataclass(frozen=True)` 사용 |
| 자치구 연결 기준 | 전처리 데이터 명세에 명시 | `district_code`로 `BusStop`과 `District` 연결 |
| `get_district()` 반환값 | README에서 형식 미지정 | 자치구 **이름 문자열** 반환 |
| `get_location()` 반환 순서 | README에서 형식 미지정 | **(위도, 경도)** 튜플 반환 |
| 객체 변환·반환 인터페이스 | 팀장 설계도에 파일명 미지정 | `utils/model_factory.py` 추가, 리스트와 코드 기반 딕셔너리 반환 |
| 전처리 결과 로딩 | 팀장 설계도에 파일명 미지정 | `load_models.py` 추가, `data/processed/` 이용 |
| 주민등록인구 | README에 속성 명시, 현행 데이터에 누락 | `population=None` 유지, 생활인구로 대체하지 않음 |
| 분석 메서드 | 팀장 README에 명시 | D 담당 영역으로 남겨둠 |

**협업 시 주의:** `District`의 생성자 매개변수 및 속성 이름은 `model_factory.py`에서 사용 중입니다. 이를 변경한다면 팩토리와 함께 호환성을 검토해야 합니다. 자치구 코드 기반 딕셔너리 반환 형식과 `population=None` 처리 역시 후속 분석 코드에 영향을 줄 수 있습니다.

## 9. 현재 상태와 범위

- **구현:** C 담당 기본 모델 2개, 객체 변환 함수, 전처리 결과 실행 예시, 관련 테스트
- **검증:** 제공된 처리 완료 데이터 기준 테스트 7개 통과
- **남은 통합 작업:** 담당자 D의 `District` 분석 메서드 구현과 후속 대시보드 코드와의 인터페이스 연동 및 전체 통합 검증

본 문서는 담당자 C의 **현재 구현 상태만** 기록합니다. 팀원 대상 중간 보고 및 D 담당자 협의 사항의 세부 메시지는 별도로 작성합니다.
