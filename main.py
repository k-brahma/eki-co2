import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('EKISPERT_API_KEY')

base_url = 'https://api.ekispert.jp/v1/json/search/course/plain?key={API_KEY}&from={station_from}&to={station_to}'

stations_list = [
    ["有楽町", "新橋"],
    ["新橋", "品川"],
    ["品川", "五反田"],
]

for station in stations_list:
    station_from = station[0]
    station_to = station[1]

    # APIリクエスト
    url = base_url.format(API_KEY=api_key, station_from=station_from, station_to=station_to)
    response = requests.get(url)
    data = response.json()

    # 最初の経路を取得
    course = data['ResultSet']['Course'][0]

    # 結果を表示
    print(f"{station_from} → {station_to}")
    print(f"co2排出量:{course['Route']['exhaustCO2']}")
