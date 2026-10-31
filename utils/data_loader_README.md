## 작업용 저장소 구조
이 저장소는 A·B 담당자가 DataLoader를 함께 구현할 때 참고하는 내부 작업용 저장소입니다.

```text
bus-data-loader/
├── README.md                # A·B 역할, 구현 순서, 공통 데이터 규칙
├── requirements.txt         # 필요한 패키지들을 기입해서 나중에 한번에 불러오기
├── .gitignore
├── main.py                  # 경로·기준 날짜 설정, 실행·결과 저장
│
├── src/
│   └── data_loader.py       # DataLoader 클래스 구현
│
├── data/
│   ├── raw/                 # 원본 데이터
│   │   ├── bus_stops.csv #버스정류소위치정보 데이터
│   │   ├── living_population.csv #자치구별 서울 생활인구 데이터
│   │   └── districts/ #자치구지도 데이터
│   │       ├── districts.shp
│   │       ├── districts.shx
│   │       ├── districts.dbf
│   │       ├── districts.prj
│   │       └── districts.cpg
│   │
│   └── processed/           # 실행 후 생성되는 결과
│       ├── bus_stops.csv
│       ├── districts.geojson
│       └── validation_report.json
│
└── tests/
    └── test_data_loader.py  # 데이터 결합·집계 결과 검증
```

- `main.py`는 실행 설정과 결과 저장을 담당하고, 데이터 읽기·정제·결합은 `DataLoader`에서 처리합니다.
- `raw/`에는 원본을 보관하고 직접 수정하지 않습니다. 위 CSV 이름에 맞춰 파일을 준비하거나 실행 경로를 조정합니다.
- 자치구 경계의 `.shp`, `.shx`, `.dbf`, `.prj`, `.cpg` 파일은 함께 보관합니다.
- `processed/` 내부 파일은 구현 완료 후 실행하면서 생성합니다. 경계 정보가 포함된 자치구 결과는 GeoJSON으로 저장합니다.

## A·B 작업 분담

| 담당 | 작업 범위 |
|---|---|
| A | 원본 파일 준비, DataLoader의 `__init__()`, `load_data()`, 필요한 패키지 정리 |
| B | `clean_bus_stops()`, `clean_population()`, `clean_districts()`, `assign_districts()`, `summarize_districts()` |
| 공동 | `run()`, `main.py`, README, 결과 검증 및 오류 처리 기준 합의 |

## 메서드별 작업과 결과

메서드는 8개입니다. 데이터셋마다 메서드 하나가 한 가지 일을 맡고, `run()`이 순서대로 직접 부릅니다. 별도의 검증 메서드 없이 검증은 각 메서드 안에서 수행합니다.

| 메서드 | 작업 | 결과 |
|---|---|---|
| `__init__(raw_dir, target_date)` | 원본 폴더로 파일 경로 3개 만들기, 기준 날짜 저장, 내부 변수 초기화 | 데이터 변수는 `None`, 검증 기록은 빈 사전 |
| `load_data()` | CSV 2개와 SHP 파일 읽기 | 원본 표 3개와 원본 행 수 기록 |
| `clean_bus_stops()` | 한강선착장·빈 ID·빈 이름·잘못된 좌표·중복 제거, 같은 ID 충돌은 기록 후 제외 | 정류장 표 |
| `clean_population()` | 기준 날짜의 자치구 25개 선택, 인구 누락 검사 | 하루치 생활인구 표 |
| `clean_districts()` | 코드·이름 정리, 코드·개수 검사, 깨진 도형 복구 | 정리된 경계 표 |
| `assign_districts()` | 공간 조인으로 정류장에 자치구 붙이기, 서울 밖·복수 배정 정류장 기록 후 제외 | 자치구가 붙은 정류장 표 |
| `summarize_districts()` | 코드 일치 확인, 면적·생활인구·정류장 수 결합, 최종 결과 검증 | 자치구별 요약표 |
| `run()` | 위 메서드를 순서대로 실행 | 정류장 표, 자치구 표, 검증 기록 반환 |

`run()`을 제외한 메서드는 결과를 반환하지 않고 `self` 속성에 저장합니다. 순서를 어기거나 같은 단계를 두 번 부르면 `RuntimeError`가 납니다.

## 공통 변수명 및 열 이름

- `self.bus_stop_data`: 정류장 표. `stop_id`, `stop_name`, `longitude`, `latitude`를 사용하고 병합 후 `district_code`, `district_name`을 추가합니다.
- `self.population_data`: 선택 날짜의 자치구별 생활인구 표. `date`, `district_code`, `district_name`, `living_population`을 사용합니다. 병합 단계에서는 수정하지 않고 인구 값을 가져다 사용합니다.
- `self.district_data`: 처음에는 자치구 경계 표이며, 병합 후 자치구별 최종 요약표로 저장합니다. 최종 열은 `district_code`, `district_name`, `geometry`, `area_km2`, `living_population`, `population_date`, `bus_stop_count`입니다.
- `self.validation_report`: 원본 행 수, 제외·중복·충돌 행 수, 미배정 정류장 수, 인구가 연결되지 않은 자치구 목록 등을 기록하는 사전입니다.

최종 데이터 표는 **정류장 표 1개와 자치구별 요약표(생활인구데이터 + 자치구지도데이터) 1개**입니다. 생활인구 표는 요약표를 만드는 중간 데이터이며 따로 반환하지 않습니다. 원본 파일은 수정하지 않습니다.

## 데이터 처리 흐름

```text
DataLoader('data/raw', '20261004'):
    파일 경로 3개와 분석 기준 날짜 저장
    데이터 변수와 검증 기록 초기화

load_data():
    버스정류소 CSV, 생활인구 CSV, 자치구 경계 SHP 읽기

clean_bus_stops():      정류장 정리         11,236 → 11,228
clean_population():     기준일 자치구 선택   35,672 → 25
clean_districts():      경계 정리           25 → 25

assign_districts():     정류장에 자치구 붙이기 11,228 → 11,215 (서울 밖 13개 제외)
summarize_districts():  면적·생활인구·정류장 수 결합 후 최종 검증 → 25

run():
    위 순서대로 실행
    정류장 표, 자치구 표, 검증 기록 반환
```

실제 구현 전에 **각 파일의 원본 열 이름과 자치구 코드 체계가 서로 맞는지** 확인하면 됩니다. 코드 체계가 다르면 `summarize_districts()` 전에 대응표로 통일하는 과정이 필요합니다.
