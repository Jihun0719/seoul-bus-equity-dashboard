from pathlib import Path

import geopandas as gpd
import pandas as pd


class DataLoader:
    ENCODINGS = ('utf-8-sig', 'cp949')
    SHP_COMPANIONS = ('.shx', '.dbf', '.prj')

    BUS_FILE = '서울시 버스정류소 위치정보.csv'
    POPULATION_FILE = '자치구별 서울 생활인구(250m) 일별집계표.csv'
    DISTRICT_FILE = 'districts/districts.shp'

    BUS_COLUMNS = {'노드 ID': 'stop_id', '정류소명': 'stop_name',
                   'X좌표': 'longitude', 'Y좌표': 'latitude'}
    POPULATION_COLUMNS = {'기준일ID': 'date', '시구코드': 'district_code',
                          '시구명': 'district_name',
                          '총생활인구수': 'living_population'}
    DISTRICT_COLUMNS = {'SIGNGU_CD': 'district_code',
                        'SIGNGU_NM': 'district_name'}

    STOP_TYPE_COLUMN = '정류소 타입'
    EXCLUDED_STOP_TYPES = ('한강선착장',)    # 버스 정류장이 아님
    SEOUL_TOTAL_CODE = '11000'              # 생활인구의 서울시 합계 행
    DISTRICT_COUNT = 25

    BUS_CRS = 'EPSG:4326'
    AREA_CRS = 'EPSG:5179'                  # 미터 단위
    MAP_CRS = 'EPSG:4326'

    # [A] 생성

    def __init__(self, raw_dir, target_date):
        raw_dir = Path(raw_dir)
        self.bus_file = raw_dir / self.BUS_FILE
        self.population_file = raw_dir / self.POPULATION_FILE
        self.district_file = raw_dir / self.DISTRICT_FILE
        self.target_date = str(target_date).replace('-', '')   # 'YYYYMMDD'

        self.bus_stop_data = None
        self.population_data = None
        self.district_data = None
        self.validation_report = {}

    # [A] 읽기

    def load_data(self):
        for path in (self.bus_file, self.population_file, self.district_file):
            if not path.exists():
                raise FileNotFoundError(f'파일이 없습니다: {path}')

        # ① CSV 2개: UTF-8로 먼저 읽고, 안 되면 CP949로 다시 읽는다
        #    ID·코드는 앞자리 0이 사라지지 않게 문자열로 읽는다
        tables = []
        for path, dtype in ((self.bus_file, {'노드 ID': str, '정류소번호': str}),
                            (self.population_file, {'기준일ID': str, '시구코드': str})):
            for encoding in self.ENCODINGS:
                try:
                    tables.append(pd.read_csv(path, encoding=encoding,
                                              dtype=dtype, thousands=','))
                    break
                except UnicodeDecodeError:
                    pass
            else:
                raise ValueError(f'{path.name}: {self.ENCODINGS} 인코딩으로 읽지 못했습니다')
        self.bus_stop_data, self.population_data = tables

        # ② 자치구 경계 SHP: 함께 있어야 하는 파일부터 확인한다
        path = self.district_file
        missing = [ext for ext in self.SHP_COMPANIONS
                   if not path.with_suffix(ext).exists()]
        if missing:
            raise FileNotFoundError(
                f'{path.name}와 함께 있어야 할 파일이 없습니다: {missing}')
        # .cpg가 없으면 국내 shp는 대부분 CP949라 한글이 깨지지 않게 지정한다
        options = {} if path.with_suffix('.cpg').exists() else {'encoding': 'cp949'}
        self.district_data = gpd.read_file(path, **options)

        self.validation_report['raw_rows'] = {
            'bus_stops': len(self.bus_stop_data),
            'population': len(self.population_data),
            'districts': len(self.district_data),
        }
        self.validation_report['district_crs'] = str(self.district_data.crs)

    # [B] 정제: 데이터셋마다 하나씩

    def clean_bus_stops(self):
        raw = self.bus_stop_data
        if raw is None:
            raise RuntimeError('load_data()를 먼저 실행해야 합니다')
        if 'stop_id' in raw:
            raise RuntimeError('이미 clean_bus_stops()를 실행했습니다')
        needed = [*self.BUS_COLUMNS, self.STOP_TYPE_COLUMN]
        missing = [c for c in needed if c not in raw.columns]
        if missing:
            raise ValueError(f'버스정류소 데이터에 필요한 열이 없습니다: {missing}')

        # ① 필요한 열만 남기고 영어 이름으로 바꾼 뒤 한강선착장을 뺀다
        stops = raw[needed].rename(columns=self.BUS_COLUMNS)
        is_excluded = stops.pop(self.STOP_TYPE_COLUMN).isin(self.EXCLUDED_STOP_TYPES)
        stops = stops[~is_excluded].copy()

        # ② 공백 제거 & 숫자 변환 ' 서울역' -> '서울역' & '126.98' -> 126.98
        for col in ('stop_id', 'stop_name'):
            stops[col] = stops[col].str.strip()
        for col in ('longitude', 'latitude'):
            stops[col] = pd.to_numeric(stops[col], errors='coerce')

        # ③ ID·이름이 비었거나 좌표가 이상한 행, 완전히 같은 중복 행을 뺀다
        is_invalid = (stops['stop_id'].fillna('').eq('')
                      | stops['stop_name'].fillna('').eq('')
                      | ~stops['longitude'].between(-180, 180)   # NaN도 걸린다
                      | ~stops['latitude'].between(-90, 90))
        stops = stops[~is_invalid]
        rows_before = len(stops)
        stops = stops.drop_duplicates()

        # ④ 같은 ID에 다른 정보가 있으면 어느 쪽이 맞는지 모르므로 기록하고 뺀다
        is_conflict = stops['stop_id'].duplicated(keep=False)
        conflicting_ids = sorted(stops.loc[is_conflict, 'stop_id'].unique())
        stops = stops[~is_conflict]

        self.bus_stop_data = stops.reset_index(drop=True)
        self.validation_report['bus_stops'] = {
            'excluded_stop_types': int(is_excluded.sum()),
            'invalid_rows': int(is_invalid.sum()),
            'duplicate_rows': rows_before - int(is_conflict.sum()) - len(stops),
            'conflicting_stop_ids': conflicting_ids,
            'rows': len(stops),
        }

    def clean_population(self):
        raw = self.population_data
        if raw is None:
            raise RuntimeError('load_data()를 먼저 실행해야 합니다')
        if 'date' in raw:
            raise RuntimeError('이미 clean_population()을 실행했습니다')
        missing = [c for c in self.POPULATION_COLUMNS if c not in raw.columns]
        if missing:
            raise ValueError(f'생활인구 데이터에 필요한 열이 없습니다: {missing}')

        # ① 필요한 열만 남기고 영어 이름으로, 인구는 숫자로
        people = raw[list(self.POPULATION_COLUMNS)].rename(columns=self.POPULATION_COLUMNS)
        people['date'] = people['date'].str.strip()
        people['district_code'] = people['district_code'].str.strip()
        people['living_population'] = pd.to_numeric(
            people['living_population'], errors='coerce')

        # ② target_date의 자치구 행만 남긴다 (11000 서울 합계 행 제외)
        day = people[(people['date'] == self.target_date)
                     & (people['district_code'] != self.SEOUL_TOTAL_CODE)
                     ].drop_duplicates()

        # ③ 검사: 날짜 없음, 같은 구 두 번, 25개 아님, 인구 0 이하·빈칸
        if len(day) == 0:
            raise ValueError(
                f'{self.target_date} 날짜의 생활인구가 없습니다 '
                f'(데이터 기간 {people["date"].min()}~{people["date"].max()})')
        if day['district_code'].duplicated().any():
            raise ValueError(f'{self.target_date}에 같은 자치구가 여러 행 있습니다')
        if len(day) != self.DISTRICT_COUNT:
            raise ValueError(f'{self.target_date}에 자치구가 {len(day)}개뿐입니다')
        # 인구 누락을 0으로 채우지 않고 멈춘다 (NaN도 걸린다)
        bad = day.loc[~(day['living_population'] > 0), 'district_code'].tolist()
        if bad:
            raise ValueError(f'생활인구가 비었거나 0 이하인 자치구: {bad}')

        self.population_data = day.reset_index(drop=True)
        self.validation_report['population'] = {'date': self.target_date,
                                                'rows': len(day)}

    def clean_districts(self):
        raw = self.district_data
        if raw is None:
            raise RuntimeError('load_data()를 먼저 실행해야 합니다')
        if 'district_code' in raw:
            raise RuntimeError('이미 clean_districts()를 실행했습니다')
        missing = [c for c in [*self.DISTRICT_COLUMNS, 'geometry'] if c not in raw.columns]
        if missing:
            raise ValueError(f'자치구 경계 데이터에 필요한 열이 없습니다: {missing}')
        if raw.crs is None:
            raise ValueError('자치구 경계에 좌표계 정보(.prj)가 없습니다')

        # ① 코드·이름·도형만 남기고 코드를 '11110' 모양으로 맞춘다 (11110.0 → '11110')
        districts = raw[[*self.DISTRICT_COLUMNS, 'geometry']].rename(
            columns=self.DISTRICT_COLUMNS)
        districts['district_code'] = (districts['district_code'].astype(str)
                                      .str.strip().str.removesuffix('.0'))
        districts['district_name'] = districts['district_name'].astype(str).str.strip()

        # ② 검사: 코드가 숫자가 아님, 중복, 25개 아님
        if not districts['district_code'].str.isdigit().all():
            raise ValueError('자치구 경계에 비었거나 숫자가 아닌 코드가 있습니다')
        if districts['district_code'].duplicated().any():
            raise ValueError('자치구 경계에 중복된 코드가 있습니다')
        if len(districts) != self.DISTRICT_COUNT:
            raise ValueError(f'자치구 경계가 {len(districts)}개입니다')

        # ③ 유효하지 않은 도형(예: 경계선이 자기 자신을 가로지름)만 고친다
        is_broken = ~districts.is_valid
        if is_broken.any():
            districts.loc[is_broken, 'geometry'] = districts[is_broken].make_valid()

        self.district_data = districts.reset_index(drop=True)
        self.validation_report['districts'] = {
            'rows': len(districts), 'crs': str(districts.crs),
            'fixed_geometries': int(is_broken.sum())}

    # [B] 병합

    def assign_districts(self):
        stops, districts = self.bus_stop_data, self.district_data
        if stops is None or 'stop_id' not in stops or 'district_code' not in districts:
            raise RuntimeError('정류장과 경계를 먼저 정제해야 합니다')
        if 'district_code' in stops:
            raise RuntimeError('이미 assign_districts()를 실행했습니다')

        # ① 정류장 좌표가 어느 구 경계 안에 있는지 공간 조인으로 찾는다
        points = gpd.GeoDataFrame(
            stops,
            geometry=gpd.points_from_xy(stops['longitude'], stops['latitude']),
            crs=self.BUS_CRS,
        ).to_crs(districts.crs)
        joined = gpd.sjoin(points, districts, predicate='intersects')

        # ② 서울 밖(미배정)이나 경계 위(복수 배정) 정류장은 기록하고 뺀다.
        #    가장 가까운 구에 억지로 넣지 않는다.
        match_count = joined.index.value_counts()
        multiple = match_count.index[match_count > 1].sort_values()
        unassigned = points.index.difference(joined.index)
        kept = joined[~joined.index.isin(multiple)]

        self.bus_stop_data = pd.DataFrame(
            kept[[*stops.columns, 'district_code', 'district_name']]
        ).reset_index(drop=True)
        self.validation_report['merge'] = {
            'assigned_stops': len(self.bus_stop_data),
            'unassigned_stops': len(unassigned),
            'unassigned_stop_ids': points.loc[unassigned, 'stop_id'].tolist(),
            'multiple_assigned_stops': len(multiple),
            'multiple_assigned_stop_ids': points.loc[multiple, 'stop_id'].tolist(),
        }

    def summarize_districts(self):
        stops, districts, people = (self.bus_stop_data, self.district_data,
                                    self.population_data)
        if stops is None or 'district_code' not in stops:
            raise RuntimeError('assign_districts()를 먼저 실행해야 합니다')
        if 'area_km2' in districts:
            raise RuntimeError('이미 summarize_districts()를 실행했습니다')

        # ① 경계와 생활인구의 구 코드 25개가 같은지 확인한다
        district_codes = set(districts['district_code'])
        population_codes = set(people['district_code'])
        if district_codes != population_codes:
            raise ValueError(
                '경계와 생활인구의 자치구 코드가 다릅니다. '
                f'경계에만: {sorted(district_codes - population_codes)}, '
                f'인구에만: {sorted(population_codes - district_codes)}')

        # ② 면적을 미터 좌표계에서 먼저 계산하고, 인구·기준일·정류장 수를 붙인 뒤
        #    지도용 경위도로 바꾼다
        summary = districts.copy()
        meters = summary if summary.crs.is_projected else summary.to_crs(self.AREA_CRS)
        summary['area_km2'] = meters.area / 1_000_000
        summary['living_population'] = summary['district_code'].map(
            people.set_index('district_code')['living_population'])
        summary['population_date'] = self.target_date  # 생활인구 기준 날짜 (YYYYMMDD)
        summary['bus_stop_count'] = (summary['district_code']
                                     .map(stops['district_code'].value_counts())
                                     .fillna(0).astype(int))
        summary = summary.to_crs(self.MAP_CRS)

        # ③ 앞 단계가 나중에 바뀌어도 틀린 결과가 조용히 저장되지 않게 확인한다
        errors = []
        if len(summary) != self.DISTRICT_COUNT:
            errors.append(f'자치구가 {len(summary)}개입니다')
        if summary['district_code'].duplicated().any():
            errors.append('자치구 코드가 중복됩니다')
        missing = summary.loc[summary['living_population'].isna(), 'district_code']
        if len(missing) > 0:
            errors.append(f'생활인구가 없는 자치구: {missing.tolist()}')
        if not (summary['area_km2'] > 0).all():
            errors.append('면적이 0 이하인 자치구가 있습니다')
        if summary['bus_stop_count'].sum() != len(stops):
            errors.append('구별 정류장 수 합계가 배정된 정류장 수와 다릅니다')
        if errors:
            raise ValueError('병합 결과 검증 실패: ' + '; '.join(errors))

        self.district_data = summary

    # [공동] 실행

    def run(self):
        self.load_data()
        self.clean_bus_stops()
        self.clean_population()
        self.clean_districts()
        self.assign_districts()
        self.summarize_districts()
        return self.bus_stop_data, self.district_data, self.validation_report


# 사용 예:
#   loader = DataLoader('data/raw', '20261004')
#   stops, districts, report = loader.run()
