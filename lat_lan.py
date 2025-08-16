import requests
import urllib.parse


def gsi_geocoding(address):
    """国土地理院APIで住所から緯度経度を取得"""
    encoded_address = urllib.parse.quote(address)
    url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={encoded_address}"

    response = requests.get(url)
    data = response.json()

    if data and len(data) > 0:
        result = data[0]
        return {
            'lat': result['geometry']['coordinates'][1],
            'lon': result['geometry']['coordinates'][0],
            'address': result['properties']['title']
        }
    return None


def gsi_distance(lat1, lon1, lat2, lon2):
    """国土地理院APIで2点間距離を計算"""
    url = "http://vldb.gsi.go.jp/sokuchi/surveycalc/surveycalc/bl2st_calc.pl"
    params = {
        'outputType': 'json',  # JSON出力
        'ellipsoid': 'GRS80',  # 測地系
        'latitude1': lat1,  # 出発点緯度
        'longitude1': lon1,  # 出発点経度
        'latitude2': lat2,  # 到着点緯度
        'longitude2': lon2  # 到着点経度
    }

    response = requests.get(url, params=params)
    data = response.json()
    return float(data['OutputData']['geoLength'])  # メートル単位

# 使用例
loc_from = gsi_geocoding("東京都千代田区丸の内1-1")
print(f"緯度: {loc_from['lat']}, 経度: {loc_from['lon']}")

loc_to=gsi_geocoding("東京都千代田区有楽町二丁目9-17")
print(f"緯度: {loc_to['lat']}, 経度: {loc_to['lon']}")

distance = gsi_distance(loc_from['lat'], loc_from['lon'], loc_to['lat'], loc_to['lon'])
print(f"距離: {distance:.2f}m")
