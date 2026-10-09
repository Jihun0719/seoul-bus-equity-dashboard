import geopandas as gpd
from models.district import District

# 실제 자치구 데이터 불러오기
data = gpd.read_file("data/processed/districts.geojson")

# District 객체 생성
districts = []

for _, row in data.iterrows():
    district = District(
        district_name=row["district_name"],
        area=row["area_km2"],
        population=None,
        living_population=row["living_population"],
        bus_stop_count=int(row["bus_stop_count"])
    )
    districts.append(district)

# 각 자치구의 두 지표 계산
densities = [d.calculate_stop_density() for d in districts]
populations = [d.calculate_stops_per_population() for d in districts]

# 최솟값과 최댓값 구하기
density_min = min(densities)
density_max = max(densities)
population_min = min(populations)
population_max = max(populations)

# 실제 형평성 점수 계산
for district in districts:
    score = district.calculate_equity_score(
        density_min,
        density_max,
        population_min,
        population_max
    )

    print(f"{district.district_name}: {score:.2f}점")
    assert 0 <= score <= 100

assert len(districts) == 25
print("\n25개 자치구 테스트 통과!")