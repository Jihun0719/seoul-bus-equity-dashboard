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
| A | 원본 파일 준비, DataLoader의  `__init__()`, `load_data()`, 필요한 패키지 정리 |
| B | `clean_data()`, `merge_data()` |
| 공동 | `run()`, `main.py`, README, 결과 검증 및 오류 처리 기준 합의 |

## 메서드별 작업과 결과

별도의 검증 메서드 없이 원본 데이터 검증은 `clean_data()`에서, 자치구 매핑·집계 결과 검증은 `merge_data()` 마지막에서 수행합니다.

| 메서드 | 작업 | 결과 |
|---|---|---|
| `__init__()` | 파일 경로·기준 날짜 저장, 내부 변수 초기화 | 데이터 변수는 `None`, 검증 기록은 빈 사전 |
| `load_data()` | CSV 2개와 압축 해제된 SHP 파일 읽기 | 원본 표 3개와 원본 행 수 기록 |
| `clean_data()` | 열 이름·자료형 정리, 날짜 선택, 중복·누락·경계 검증 | 정제된 표 3개 |
| `merge_data()` | 정류장 자치구 매핑, 면적 계산, 구별 정류장 집계, 생활인구 연결 및 결과 검증 | 최종 표 2개와 검증 기록 |
| `run()` | 읽기 → 정제 → 병합 순서로 실행 | 정류장 표, 자치구 표, 검증 기록 반환 |

`load_data()`, `clean_data()`, `merge_data()`는 결과를 별도로 반환하지 않고 `self` 속성에 저장합니다. `run()`이 마지막에 결과를 반환합니다. Python 틀의 본문은 `pass`로 남겨두었으므로 이 순서에 맞게 직접 구현합니다.

## 공통 변수명 및 열 이름

- `self.bus_stop_data`: 정류장 표. `stop_id`, `stop_name`, `longitude`, `latitude`를 사용하고 병합 후 `district_code`, `district_name`을 추가합니다.
- `self.population_data`: 선택 날짜의 자치구별 생활인구 표. `date`, `district_code`, `district_name`, `living_population`을 사용합니다. 병합 단계에서는 수정하지 않고 인구 값을 가져다 사용합니다.
- `self.district_data`: 처음에는 자치구 경계 표이며, 병합 후 자치구별 최종 요약표로 저장합니다. 최종 열은 `district_code`, `district_name`, `geometry`, `area_km2`, `living_population`, `bus_stop_count`입니다.
- `self.validation_report`: 원본 행 수, 제외·중복·충돌 행 수, 미배정 정류장 수, 인구가 연결되지 않은 자치구 목록 등을 기록하는 사전입니다.

최종 데이터 표는 **정류장 표 1개와 자치구별 요약표(생활인구데이터 + 자치구지도데이터) 1개**입니다. 생활인구 표는 요약표를 만드는 중간 데이터이며 따로 반환하지 않습니다. 원본 파일은 수정하지 않습니다.

## 데이터 처리 흐름

```text
DataLoader 생성:
    파일 경로 3개와 분석 기준 날짜 저장
    데이터 변수와 검증 기록 초기화

load_data():
    버스정류소 CSV 읽기
    생활인구 CSV 읽기
    자치구 경계 SHP 읽기

clean_data():
    필요한 열 확인, 열 이름과 자료형 통일
    중복·누락·잘못된 값 확인 및 처리
    선택 날짜의 자치구별 생활인구 추출
    자치구 코드와 경계 확인
    처리 내역 기록

merge_data():
    정류장 좌표로 자치구를 찾아 컬럼 추가
    자치구별 정류장 수 집계
    자치구 경계로 면적 계산
    생활인구·정류장 수·면적·경계를 자치구별 표로 결합
    매핑·집계 결과 확인 및 기록

run():
    load_data() → clean_data() → merge_data()
    정류장 표, 자치구 표, 검증 기록 반환
```

실제 구현 전에 **각 파일의 원본 열 이름과 자치구 코드 체계가 서로 맞는지** 확인하면 됩니다. 코드 체계가 다르면 `merge_data()` 전에 대응표로 통일하는 과정이 필요합니다.
