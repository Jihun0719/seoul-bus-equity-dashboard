# 전처리 결과를 data/processed에 저장합니다. 기존 결과를 사용할 때는 다시 실행할 필요가 없습니다.
import json
import sys
from pathlib import Path

from utils.data_loader import DataLoader

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / 'data' / 'raw'
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'

TARGET_DATE = '20261004'    # 데이터의 마지막 날. 원본에 2024-02-29는 없다.


class ResultSaver:
    def __init__(self, out_dir):
        self.out_dir = Path(out_dir)

    def save(self, stops, districts, report):
        self.out_dir.mkdir(parents=True, exist_ok=True)
        stops.to_csv(self.out_dir / 'bus_stops.csv',
                     index=False, encoding='utf-8-sig')   # 엑셀에서 한글 깨짐 방지
        districts.to_file(self.out_dir / 'districts.geojson', driver='GeoJSON')
        with open(self.out_dir / 'validation_report.json', 'w',
                  encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


def show_summary(loader, report):
    print(loader)
    print(f'서울 밖이라 제외한 정류장: {report["merge"]["unassigned_stops"]}개')
    print(f'한강선착장으로 제외한 정류장: '
          f'{report["bus_stops"]["excluded_stop_types"]}개')
    table = loader.district_data.drop(columns='geometry')
    table = table.sort_values('bus_stop_count', ascending=False)
    print(table.to_string(index=False))


def main():
    # python process.py 20260901 처럼 날짜를 줄 수 있다
    target_date = sys.argv[1] if len(sys.argv) > 1 else TARGET_DATE
    loader = DataLoader.from_folder(RAW_DIR, target_date)
    saver = ResultSaver(PROCESSED_DIR)

    try:
        stops, districts, report = loader.run()
    except FileNotFoundError as e:
        print('원본 파일을 찾지 못했습니다:', e)
        return
    except ValueError as e:
        print('데이터에 문제가 있습니다:', e)
        return

    saver.save(stops, districts, report)
    show_summary(loader, report)
    print('저장 위치:', PROCESSED_DIR)


if __name__ == '__main__':
    main()
