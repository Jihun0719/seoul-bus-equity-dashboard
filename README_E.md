# E 담당 구현 보고서 — 지도 시각화 및 대시보드 메인 화면

## 1. 담당 범위 및 구현 개요

본 프로젝트는 **서울시 자치구별 버스 인프라 형평성 대시보드**입니다. E 담당은 A·B 담당의 전처리 데이터, C 담당의 객체 모델, D 담당의 지표 계산 메서드를 이용해 **서울시 25개 자치구 지도와 Streamlit 대시보드 기본 화면**을 구현했습니다.

- `utils/visualizer.py`: `Visualizer` 클래스, 자치구 단계구분도(Choropleth Map), 선택 자치구 확대 및 버스정류소 표시
- `app.py`: Streamlit 메인 화면, 데이터 로딩, 지표 선택, 지도 선택 이벤트 및 상세 정보 표시
- `tests/test_visualizer.py`: 지도 데이터와 시각화 기능 검증
- `requirements.txt`: E 담당에서 사용하는 `streamlit`, `plotly` 추가 필요

F 담당의 막대그래프와 산점도는 **아직 구현하지 않았으며**, 화면에 연동 예정 영역만 마련했습니다.

## 2. 기존 담당 코드와의 연동

| 담당 | 활용 파일 및 기능 | E 담당에서의 활용 |
|---|---|---|
| A·B | `data/processed/bus_stops.csv`, `districts.geojson` | 정류소 위치 및 자치구 경계·기초 통계 로딩 |
| C | `utils/model_factory.py`의 `create_models()` | `BusStop` 리스트와 `District` 딕셔너리 생성 |
| C | `models/bus_stop.py`, `models/district.py` | 정류소 및 자치구 속성 조회 |
| D | `District.calculate_stop_density()` | 면적 1㎢당 정류소 수 계산 |
| D | `District.calculate_stops_per_population()` | 생활인구 1만 명당 정류소 수 계산 |
| D | `District.calculate_equity_score()` | 종합 형평성 점수 계산 |

`app.py`는 `data/processed`의 결과 파일을 직접 읽어 `create_models(stops_data, districts_data)`를 호출합니다. `stop_id`와 `district_code`는 **앞자리 0을 보존하기 위해 문자열로 로딩**합니다.

현재 전처리 결과에는 주민등록인구가 없으므로 `District.population`은 `None`이며, 인구 대비 정류소 지표는 **생활인구**를 기준으로 합니다.

## 3. 구현 기능

### 3.1 `Visualizer` 클래스 (`utils/visualizer.py`)

**생성자**

```python
Visualizer(districts, bus_stops)
```

- `districts`: 자치구 코드를 키로 하는 `District` 객체 딕셔너리
- `bus_stops`: `BusStop` 객체 리스트

**`prepare_map_data()`**

25개 `District` 객체에서 지도와 차트에 공통으로 사용할 `pandas.DataFrame`을 생성합니다. 주요 열은 다음과 같습니다.

- `district_code`, `district_name`, `geometry`
- `area_km2`, `living_population`, `bus_stop_count`, `population_date`
- `stop_density`, `stops_per_population`, `equity_score`

정류소 밀도 및 형평성 점수는 D 담당의 메서드를 호출해 계산하며, 동일한 25개 자치구의 최솟값·최댓값을 정규화 기준으로 사용합니다.

**`create_map(metric="equity_score", show_bus_stops=False, selected_district_code=None)`**

Plotly `Figure` 객체를 반환합니다.

- 자치구 경계(`geometry`)를 GeoJSON으로 변환해 단계구분도 생성
- 지표에 따라 자치구별 색상 구분 및 범례 표시
- 마우스 오버 시 자치구명, 정류소 수, 밀도, 생활인구 대비 정류소 수, 종합 점수 표시
- 선택 자치구가 없으면 서울 전체 지도 표시
- `selected_district_code`가 지정되면 해당 자치구로 확대
- `show_bus_stops=True`이면 정류소 위치를 점으로 표시하며, 선택 자치구가 있으면 해당 구의 정류소만 표시
- 지원하지 않는 지표나 존재하지 않는 자치구 코드를 전달하면 `ValueError` 발생

지원 지표:

| `metric` 값 | 표시 지표 | 단위 |
|---|---|---|
| `equity_score` | 종합 형평성 점수 | 점 |
| `stop_density` | 면적당 정류소 수 | 개/㎢ |
| `stops_per_population` | 생활인구 1만 명당 정류소 수 | 개/1만 명 |

지도 색상은 밝은 주황부터 진한 파랑까지 단계적으로 구분해 가독성을 높였습니다.

### 3.2 Streamlit 메인 화면 (`app.py`)

- 제목: 서울시 자치구별 버스 인프라 형평성 대시보드
- 요약 지표: 분석 자치구 수, 배정된 정류소 수, 생활인구 기준일
- 지도 지표 선택 메뉴
- 자치구 지도 선택 시 확대 및 해당 구 정류소 표시
- `서울 전체 보기` 버튼으로 확대 상태 해제
- 전체 서울 지도에서 정류소 점 표시 여부 선택
- 선택 자치구의 정류소 수, 면적당 정류소 수, 생활인구 대비 정류소 수, 종합 점수 표시
- F 담당의 막대그래프·산점도 연동 예정 영역

지도 선택 기능은 Streamlit `st.plotly_chart(..., on_select="rerun", selection_mode="points")`와 `st.session_state`를 이용합니다. **클릭 선택 이벤트의 실제 동작은 설치된 Streamlit·Plotly 버전 및 브라우저 환경에서 확인해야 합니다.**

## 4. 실행 환경 및 방법

프로젝트 최상위 폴더에서 실행합니다. Windows PowerShell 기준 예시는 다음과 같습니다.

**가상환경 생성(최초 1회):**

```powershell
py -3.13 -m venv .venv
```

**가상환경 활성화:**

```powershell
.\.venv\Scripts\Activate.ps1
```

PowerShell 실행 정책 때문에 활성화가 차단된다면, 가상환경의 Python을 직접 실행할 수도 있습니다.

**패키지 설치:**

```powershell
python -m pip install -r requirements.txt
```

`requirements.txt`에는 기존 패키지 외에 다음 두 패키지가 포함되어야 합니다.

```text
streamlit
plotly
```

**대시보드 실행:**

```powershell
python -m streamlit run app.py
```

일반적으로 브라우저에서 `http://localhost:8501`로 접속할 수 있습니다.

**테스트 실행:**

```powershell
python -m pytest -v
```

E 담당 테스트만 실행하려면:

```powershell
python -m pytest tests/test_visualizer.py -v
```

## 5. 실행 데이터 및 지표 해석

전처리 기준일: **2026-10-04**

- 분석 대상: 서울시 **25개 자치구**
- 자치구에 배정된 버스정류소: **11,215개**
- `bus_stops.csv`와 `districts.geojson`을 사용

종합 형평성 점수는 **면적당 정류소 수와 생활인구 1만 명당 정류소 수를 각각 50% 반영한 상대 점수**입니다. 이 값만으로 실제 대중교통 접근성, 노선 빈도, 운행 간격, 정류소별 이용 편의 등을 평가할 수는 없습니다.

## 6. 테스트 및 확인 사항

`tests/test_visualizer.py`에 지도 데이터 생성과 지표·지도 기능 관련 테스트가 포함되어 있습니다. 전체 테스트는 개발 환경에서 `python -m pytest -v`로 실행합니다.

로컬 개발 과정에서 전체 테스트 통과를 확인했습니다. 단, 테스트 개수와 결과는 팀원의 최신 GitHub 코드 및 설치 환경에 따라 달라질 수 있으므로 **최종 제출 시 실제 실행 결과를 기록**해야 합니다.

**협업 관련 주의:** C 담당의 `tests/test_model_factory_processed.py`에서 Pandas 문자열 열에 정수 ID를 넣는 테스트는 Pandas 버전에 따라 대입 시점에 `TypeError`가 발생할 수 있습니다. 해당 테스트의 `numeric_id` 분기에서 `stop_id` 열을 `object`로 변환한 뒤 정수를 대입하면 의도한 검증을 수행할 수 있습니다. 이는 C 담당 테스트 파일이므로 변경 내용을 공유하고 반영 여부를 협의하는 것이 좋습니다.

## 7. F 담당자 연동 안내

F 담당자는 기존 `Visualizer` 클래스를 활용하여 다음 기능을 추가할 수 있습니다.

- `create_bar_chart()`: 자치구별 지표 비교 막대그래프
- `create_scatter_plot()`: 생활인구와 정류소 수 산점도
- 자치구 선택에 따른 차트 연동

`prepare_map_data()`는 F 담당자가 사용할 수 있는 자치구별 공통 지표 DataFrame을 반환합니다. 따라서 **지표를 다시 계산하거나 데이터 전처리를 중복 구현할 필요가 없습니다.**

`app.py` 하단의 `추가 분석 (F 담당 연동 예정)` 영역에 차트를 연결하면 됩니다. 여러 사람이 같은 파일을 수정할 경우 Git 충돌이 발생할 수 있으므로 변경 전에 인터페이스와 작업 범위를 협의해 주세요.

## 8. 파일 구조

```text
seoul-bus-equity-dashboard-main/
├── app.py                       # E: Streamlit 대시보드 메인 화면
├── requirements.txt             # E: streamlit, plotly 의존성 추가
├── README_E.md                  # E: 구현 및 실행 안내
├── models/
│   ├── bus_stop.py              # C
│   └── district.py              # C·D
├── utils/
│   ├── data_loader.py           # A·B
│   ├── model_factory.py         # C
│   └── visualizer.py            # E
├── tests/
│   └── test_visualizer.py       # E
└── data/
    └── processed/
        ├── bus_stops.csv
        ├── districts.geojson
        └── validation_report.json
```

## 9. 향후 작업

1. F 담당의 막대그래프 및 산점도 연결
2. 지도 선택과 차트 선택 상태 연동
3. 팀원들의 최신 코드 통합 및 전체 테스트 재실행
4. GitHub 최종 반영 및 실행 화면 확인

---

**담당:** E — 지도 시각화 및 대시보드 메인 레이아웃
