# Seoul Bus Infrastructure Equity Dashboard — D 담당 분석 모듈

본 문서는 담당자 D가 구현한 서울시 자치구별 버스 인프라 지표 계산 기능과 테스트 결과를 정리한 문서입니다.

## 1. 구현 내용

기존 `models/district.py` 파일의 `District` 클래스에 다음 네 가지 메서드를 추가했습니다.

### 1.1 calculate_stop_density()

자치구 면적 1km²당 버스정류장 수를 계산하는 메서드입니다.

**계산식**

정류장 밀도 = 버스정류장 수 / 자치구 면적(km²)

```python
def calculate_stop_density(self) -> float:
    """면적 1km²당 버스정류장 수를 계산합니다."""
    return self.bus_stop_count / self.area
```

### 1.2 calculate_stops_per_population()

자치구의 생활인구 1만 명당 버스정류장 수를 계산하는 메서드입니다.

**계산식**

생활인구 대비 정류장 수 = 버스정류장 수 / 생활인구 × 10,000

```python
def calculate_stops_per_population(self) -> float:
    """생활인구 1만 명당 버스정류장 수를 계산합니다."""
    if self.living_population == 0:
        raise ValueError("생활인구가 0이면 계산할 수 없습니다.")
    return self.bus_stop_count / self.living_population * 10000
```

생활인구가 0인 경우에는 `ValueError`가 발생하도록 구현했습니다.

### 1.3 normalize()

변수를 0~100점으로 변환하는 메서드입니다.
매개변수는 셋이며, 정류장 밀도 혹은 생활인구 대비 정류장 수의

**계산식**

정규화 점수 = (현재 값 - 최솟값) / (최댓값 - 최솟값) × 100

```python
@staticmethod
def normalize(value: float, min_value: float, max_value: float) -> float:
    if min_value > max_value:
        raise ValueError("최솟값은 최댓값보다 클 수 없습니다.")
    if not min_value <= value <= max_value:
        raise ValueError("값은 최솟값과 최댓값 사이에 있어야 합니다.")
    if max_value == min_value:
        return 50.0
    return (value - min_value) / (max_value - min_value) * 100
```

다음과 같은 예외 처리를 구현했습니다.

- 최솟값이 최댓값보다 크면 `ValueError` 발생
- 현재 값이 최솟값과 최댓값 사이에 없으면 `ValueError` 발생
- 최솟값과 최댓값이 같으면 50점 반환

### 1.4 calculate_equity_score()

정류장 밀도와 생활인구 대비 정류장 수를 각각 정규화한 뒤, 두 지표에 동일한 가중치를 적용하여 종합 점수를 계산하는 메서드입니다.

**계산식**

형평성 점수 = 정규화된 정류장 밀도 × 0.5 + 정규화된 생활인구 대비 정류장 수 × 0.5

```python
def calculate_equity_score(
    self,
    density_min: float,
    density_max: float,
    population_min: float,
    population_max: float
) -> float:
    density = self.calculate_stop_density()
    population = self.calculate_stops_per_population()

    density_score = self.normalize(density, density_min, density_max)
    population_score = self.normalize(population, population_min, population_max)

    return density_score * 0.5 + population_score * 0.5
```

두 지표의 가중치는 각각 50%로 설정했습니다.

최솟값과 최댓값은 메서드 외부에서 계산하여 매개변수로 전달받습니다.

## 2. 수정 및 추가 파일

| 파일 | 작업 내용 |
|---|---|
| `models/district.py` | 지표 계산 메서드 4개 추가 |
| `tests/test_equity_actual.py` | 실제 서울시 자치구 데이터 테스트 코드 작성 |
| `README_D.md` | 구현 내용 및 테스트 결과 문서화 |

## 3. 테스트

### 3.1 기본 계산 테스트

임의의 자치구 데이터를 생성하여 각 계산 메서드가 정상적으로 동작하는지 확인했습니다.

**테스트 코드**

```python
from models.district import District

district = District(
    district_name="테스트구",
    area=20.0,
    population=None,
    living_population=100000,
    bus_stop_count=200
)

print(district.calculate_stop_density())
print(district.calculate_stops_per_population())
print(district.calculate_equity_score(5, 15, 10, 30))
```

**실행 결과**

```text
10.0
20.0
50.0
```

### 3.2 예외 처리 테스트

최솟값이 최댓값보다 큰 경우 정상적으로 오류가 발생하는지 확인했습니다.

**테스트 코드**

```python
District.normalize(15, 20, 10)
```

**실행 결과**

```text
ValueError: 최솟값은 최댓값보다 클 수 없습니다.
```

### 3.3 실제 데이터 테스트

`data/processed/districts.geojson` 파일을 사용하여 서울시 25개 자치구의 형평성 점수를 계산했습니다.

**테스트 내용**

- 서울시 25개 자치구 데이터 불러오기
- 자치구별 정류장 밀도 계산
- 자치구별 생활인구 대비 정류장 수 계산
- 두 지표의 최솟값과 최댓값 계산
- 최소-최대 정규화 적용
- 두 지표에 각각 50% 가중치 적용
- 계산된 형평성 점수가 0~100점 범위에 있는지 확인

**실행 명령어**

프로젝트 최상위 폴더의 PowerShell 터미널에서 실행합니다.

```powershell
$env:PYTHONPATH = "."
py tests/test_equity_actual.py
```

### 3.4 서울시 25개 자치구 형평성 점수 계산 결과

| 자치구 | 형평성 점수 |
|---|---:|
| 종로구 | 56.96 |
| 중구 | 50.04 |
| 용산구 | 31.27 |
| 성동구 | 90.96 |
| 광진구 | 18.65 |
| 동대문구 | 39.94 |
| 중랑구 | 42.81 |
| 성북구 | 77.48 |
| 강북구 | 52.42 |
| 도봉구 | 40.66 |
| 노원구 | 19.54 |
| 은평구 | 32.78 |
| 서대문구 | 84.96 |
| 마포구 | 73.93 |
| 양천구 | 27.30 |
| 강서구 | 22.80 |
| 구로구 | 73.58 |
| 금천구 | 98.50 |
| 영등포구 | 44.96 |
| 동작구 | 77.68 |
| 관악구 | 23.03 |
| 서초구 | 31.92 |
| 강남구 | 6.57 |
| 송파구 | 6.35 |
| 강동구 | 23.15 |

**테스트 결과**

서울시 25개 자치구 모두 형평성 점수가 계산되었으며, 모든 점수가 0~100점 범위에 포함되었습니다.

- 최고 점수: 금천구 (98.50점)
- 최저 점수: 송파구 (6.35점)

## 4. 형평성 점수 해석

현재 구현한 형평성 점수는 자치구별 버스정류장 공급 수준을 상대적으로 비교하기 위한 지표입니다.

정류장 밀도와 생활인구 대비 정류장 수를 각각 정규화하여 50:50 비율로 합산했습니다.

점수가 높을수록 비교 대상 자치구 중 면적 및 생활인구 대비 버스정류장 공급 수준이 상대적으로 높음을 의미합니다.

상대적 지표임에 유의해주시길 바랍니다. 

## 5. 주의사항

### 5.1 최솟값과 최댓값 계산

`calculate_equity_score()` 메서드는 형평성 점수를 계산할 때 다음 네 가지 매개변수를 필요로 합니다.

- `density_min`: 정류장 밀도의 최솟값
- `density_max`: 정류장 밀도의 최댓값
- `population_min`: 생활인구 대비 정류장 수의 최솟값
- `population_max`: 생활인구 대비 정류장 수의 최댓값

현재 `District` 클래스는 이 값들을 직접 계산하지 않습니다.

대신 `tests/test_equity_actual.py`에서 서울시 25개 자치구의 데이터를 불러와 각 지표의 최솟값과 최댓값을 계산하고, 이를 `calculate_equity_score()`에 전달하도록 구현했습니다.

**따라서 실제 대시보드에 연동할 때는 테스트 파일에 구현된 최솟값·최댓값 계산 과정을 활용해야 합니다.**

### 5.2 정규화 기준

현재 형평성 점수는 서울시 전체 25개 자치구를 기준으로 계산했습니다.

일부 자치구만 사용하여 최솟값과 최댓값을 다시 계산하면 동일한 자치구라도 형평성 점수가 달라질 수 있습니다.
