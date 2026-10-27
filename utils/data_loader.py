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

    def __init__(self, bus_file, population_file, district_file, target_date):
        self.bus_file = Path(bus_file)
        self.population_file = Path(population_file)
        self.district_file = Path(district_file)
        self.target_date = str(target_date).replace('-', '')   # 'YYYYMMDD'

        self.bus_stop_data = None
        self.population_data = None
        self.district_data = None
        self.validation_report = {}

    @classmethod
    def from_folder(cls, raw_dir, target_date):
        raw_dir = Path(raw_dir)
        return cls(raw_dir / cls.BUS_FILE,
                   raw_dir / cls.POPULATION_FILE,
                   raw_dir / cls.DISTRICT_FILE,
                   target_date)

    def __str__(self):
        if self.district_data is None:
            return f'DataLoader({self.target_date}, 아직 실행 전)'
        return (f'DataLoader({self.target_date}, '
                f'정류장 {len(self.bus_stop_data)}개, '
                f'자치구 {len(self.district_data)}개)')

    # [A] 읽기

    def load_data(self):
        # ID·코드는 앞자리 0이 사라지지 않게 문자열로 읽는다
        self.bus_stop_data = self.read_csv(
            self.bus_file, {'노드 ID': str, '정류소번호': str})
        self.population_data = self.read_csv(
            self.population_file, {'기준일ID': str, '시구코드': str})
        self.district_data = self.read_shp(self.district_file) #자치구정보, 경계도형
        
        self.validation_report['raw_rows'] = {
            'bus_stops': len(self.bus_stop_data),
            'population': len(self.population_data),
            'districts': len(self.district_data),
        } # 표의 행 개수 저장
        self.validation_report['district_crs'] = str(self.district_data.crs) #현재 지도 데이터 좌표계 저장

    @classmethod
    def read_csv(cls, path, dtype):
        if not path.exists():
            raise FileNotFoundError(f'파일이 없습니다: {path}')
        for encoding in cls.ENCODINGS: #UTF-8 먼저 인코딩 후 맞지않음 CP949로 다시 인코딩으로 읽기!
            try:
                return pd.read_csv(path, encoding=encoding, dtype=dtype)
            except UnicodeDecodeError:
                pass
        raise ValueError(f'{path.name}: {cls.ENCODINGS} 인코딩으로 읽지 못했습니다')

    @classmethod
    def read_shp(cls, path):
        #자치구 지도 파일 .shp 읽기 path 는 .shp 파일경로 Path객체
        if not path.exists():
            raise FileNotFoundError(f'파일이 없습니다: {path}')
        #앞에 SHP_COMPANIONS에 설정한 확장자 확인으로 함께 있어야하는 파일 확인하기
        missing = [ext for ext in cls.SHP_COMPANIONS
                   if not path.with_suffix(ext).exists()] 
                    # path.with_suffix(ext)는 경로의 확장자 부분만 바꾸는 메서드
        if missing:
            raise FileNotFoundError(
                f'{path.name}와 함께 있어야 할 파일이 없습니다: {missing}')
        return gpd.read_file(path) #모두 있으면 지도 데이터 읽기(GeoDataFrame객체)으로 반환

    # [B] 정제

    def clean_data(self):
        if self.bus_stop_data is None:
            raise RuntimeError('load_data()를 먼저 실행해야 합니다')

        self.bus_stop_data, self.validation_report['bus_stops'] = \
            self.clean_bus_stops(self.bus_stop_data)
        self.population_data, self.validation_report['population'] = \
            self.clean_population(self.population_data)
        self.district_data, self.validation_report['districts'] = \
            self.clean_districts(self.district_data)

        self.check_same_codes(self.district_data, self.population_data)

    @staticmethod
    def require_columns(table, columns, label): #table: 검사할표, columns: 꼭 있어야 할 열목록 #label: 데이터이름
        missing = [c for c in columns if c not in table.columns]
        if missing:
            raise ValueError(f'{label} 데이터에 필요한 열이 없습니다: {missing}')

    def clean_bus_stops(self, raw): #raw는 정리전 원본표
        self.require_columns(raw, [*self.BUS_COLUMNS, self.STOP_TYPE_COLUMN],
                             '버스정류소')

        is_excluded = raw[self.STOP_TYPE_COLUMN].isin(self.EXCLUDED_STOP_TYPES) # raw['정류소 타입'].isin(('한강선착장',))
        table = raw[~is_excluded][list(self.BUS_COLUMNS)] #is_excluded가 아닌, 필요할 열들만 선택
        table = table.rename(columns=self.BUS_COLUMNS) #선택한 열 이름 바꾸기

        #공백 제거 & 숫자 변환 ' 서울역' -> '서울역' & '126.98' -> 126.98
        table['stop_id'] = table['stop_id'].str.strip()
        table['stop_name'] = table['stop_name'].str.strip()
        table['longitude'] = pd.to_numeric(table['longitude'], errors='coerce')
        table['latitude'] = pd.to_numeric(table['latitude'], errors='coerce')

        #정류장 id가 결측값, 경도,위도가 이상한값
        is_invalid = (table['stop_id'].isna()
                      | ~table['longitude'].between(-180, 180)   # NaN도 걸린다
                      | ~table['latitude'].between(-90, 90))
        table = table[~is_invalid]

        rows_before = len(table)
        table = table.drop_duplicates()    #4개의 열이 모두 같은 중복제거

        conflicts = table[table['stop_id'].duplicated(keep=False)] #같은 Id, 다른 정보 행 추출
        conflicting_ids = sorted(conflicts['stop_id'].unique()) #문제 Id 뽑아서 정렬
        if conflicting_ids:
            raise ValueError(f'같은 stop_id에 다른 정보가 있습니다: {conflicting_ids[:10]}') #나중에 수정 해야할듯 프로그램 종료됨

        #처리 기록
        info = {
            'excluded_stop_types': int(is_excluded.sum()),
            'invalid_rows': int(is_invalid.sum()),
            'duplicate_rows': rows_before - len(table),
            'rows': len(table),
        }
        return table.reset_index(drop=True), info

    def clean_population(self, raw):
        self.require_columns(raw, list(self.POPULATION_COLUMNS), '생활인구')

        table = raw[list(self.POPULATION_COLUMNS)] #4개의 열만 있는 Dataframe 객체
        table = table.rename(columns=self.POPULATION_COLUMNS)
        table['date'] = table['date'].str.strip()
        table['district_code'] = table['district_code'].str.strip()
        table['living_population'] = pd.to_numeric(
            table['living_population'], errors='coerce')
        table = table[table['district_code'] != self.SEOUL_TOTAL_CODE] #서울 전체 합계 행 11000 은 자치구 아님

        day = table[table['date'] == self.target_date].drop_duplicates() #target_date 날짜 행만 남기기
        if len(day) == 0:
            raise ValueError(
                f'{self.target_date} 날짜의 생활인구가 없습니다 '
                f'(기간 {table["date"].min()}~{table["date"].max()}, 빠진 날 있음)')
        if day['district_code'].duplicated().any():
            raise ValueError(f'{self.target_date}에 같은 자치구가 여러 행 있습니다')
        if len(day) != self.DISTRICT_COUNT:
            raise ValueError(f'{self.target_date}에 자치구가 {len(day)}개뿐입니다')

        # 인구 누락을 0으로 채우지 않고 멈춘다
        bad = day[~(day['living_population'] > 0)]['district_code'].tolist()
        if bad:
            raise ValueError(f'생활인구가 비었거나 0 이하인 자치구: {bad}')

        info = {'date': self.target_date, 'rows': len(day)}
        return day.reset_index(drop=True), info

    def clean_districts(self, raw):
        self.require_columns(raw, list(self.DISTRICT_COLUMNS), '자치구 경계')
        if raw.crs is None:
            raise ValueError('자치구 경계에 좌표계 정보(.prj)가 없습니다')

        table = raw[[*self.DISTRICT_COLUMNS, 'geometry']] #필요한 열만 선택 ex) 'SIGNGU_CD', 'SIGNGU_NM', 'geometry'
        table = table.rename(columns=self.DISTRICT_COLUMNS)
        table['district_code'] = table['district_code'].astype(str).str.strip() #11110        → '11110'
        table['district_name'] = table['district_name'].astype(str).str.strip() #'  종로구  ' → '종로구'

        if table['district_code'].duplicated().any():
            raise ValueError('자치구 경계에 중복된 코드가 있습니다')
        if len(table) != self.DISTRICT_COUNT:
            raise ValueError(f'자치구 경계가 {len(table)}개입니다')

        is_broken = ~table.is_valid #유효하지 않은 경계 도형(ex)다각형 경계선이 자기자신 가로지름
        if is_broken.any():
            table.loc[is_broken, 'geometry'] = table[is_broken].make_valid()

        info = {'rows': len(table), 'crs': str(table.crs),
                'fixed_geometries': int(is_broken.sum())}
        return table.reset_index(drop=True), info

    @staticmethod
    def check_same_codes(districts, population):
        district_codes = set(districts['district_code'])
        population_codes = set(population['district_code'])
        if district_codes != population_codes:
            raise ValueError(
                '경계와 생활인구의 자치구 코드가 다릅니다. '
                f'경계에만: {sorted(district_codes - population_codes)}, '
                f'인구에만: {sorted(population_codes - district_codes)}')

    # [B] 병합

    def merge_data(self):
        if self.district_data is None or 'district_code' not in self.district_data:
            raise RuntimeError('clean_data()를 먼저 실행해야 합니다')

        stops, info = self.assign_districts(self.bus_stop_data, self.district_data)
        summary = self.summarize_districts(self.district_data, stops,
                                           self.population_data)

        self.bus_stop_data = stops
        self.district_data = summary
        self.validation_report['merge'] = info
        self.check_merge_result(stops, summary)

    def assign_districts(self, stops, districts): 
        points = gpd.GeoDataFrame(
            stops,
            geometry=gpd.points_from_xy(stops['longitude'], stops['latitude']),
            crs=self.BUS_CRS,
        ).to_crs(districts.crs)
        joined = gpd.sjoin(points,
                           districts[['district_code', 'district_name', 'geometry']],
                           how='left', predicate='intersects')

        # 서울 밖(미배정)이나 경계 위(복수 배정) 정류장은 기록하고 뺀다.
        # 가장 가까운 구에 억지로 넣지 않는다.
        match_count = joined.groupby(level=0)['district_code'].count()
        unassigned = match_count.index[match_count == 0]
        multiple = match_count.index[match_count > 1]

        kept = joined[~joined.index.isin(unassigned.union(multiple))]
        columns = ['stop_id', 'stop_name', 'longitude', 'latitude',
                   'district_code', 'district_name']
        result = pd.DataFrame(kept[columns]).reset_index(drop=True)

        info = {
            'assigned_stops': len(result),
            'unassigned_stops': len(unassigned),
            'unassigned_stop_ids': points.loc[unassigned, 'stop_id'].tolist(),
            'multiple_assigned_stops': len(multiple),
            'multiple_assigned_stop_ids': points.loc[multiple, 'stop_id'].tolist(),
        }
        return result, info

    def summarize_districts(self, districts, stops, population):
        summary = districts[['district_code', 'district_name', 'geometry']].copy()

        if districts.crs.is_projected:
            meters = districts
        else:
            meters = districts.to_crs(self.AREA_CRS)
        summary['area_km2'] = meters.geometry.area / 1_000_000

        people = population.set_index('district_code')['living_population']
        counts = stops.groupby('district_code').size()
        summary['living_population'] = summary['district_code'].map(people)
        summary['population_date'] = self.target_date  # 생활인구 기준 날짜 (YYYYMMDD)
        summary['bus_stop_count'] = (
            summary['district_code'].map(counts).fillna(0).astype(int))

        # 면적을 먼저 계산한 뒤 지도용 경위도로 바꾼다
        return summary.to_crs(self.MAP_CRS)

    def check_merge_result(self, stops, districts):
        errors = []
        if len(districts) != self.DISTRICT_COUNT:
            errors.append(f'자치구가 {len(districts)}개입니다')
        if districts['district_code'].duplicated().any():
            errors.append('자치구 코드가 중복됩니다')
        missing = districts[districts['living_population'].isna()]
        if len(missing) > 0:
            errors.append(f'생활인구가 없는 자치구: {missing["district_code"].tolist()}')
        if not (districts['area_km2'] > 0).all():
            errors.append('면적이 0 이하인 자치구가 있습니다')
        if stops['stop_id'].duplicated().any():
            errors.append('여러 구에 배정된 정류장이 있습니다')
        if districts['bus_stop_count'].sum() != len(stops):
            errors.append('구별 정류장 수 합계가 배정된 정류장 수와 다릅니다')

        if errors:
            raise ValueError('병합 결과 검증 실패: ' + '; '.join(errors))

    # [공동] 실행

    def run(self):
        self.load_data()
        self.clean_data()
        self.merge_data()
        return self.bus_stop_data, self.district_data, self.validation_report


# 사용 예:
#   loader = DataLoader.from_folder('data/raw', '20261004')
#   stops, districts, report = loader.run()
