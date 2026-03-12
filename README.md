# eki-co2

通勤経路の CO2 排出量をざっくり比較するための小さな実験リポジトリです。

現在のメイン機能は [`gui.py`](/mnt/d/projects/experimentals/eki-co2/gui.py) の Tkinter アプリです。CSV を読み込み、移動手段ごとに CO2 排出量を計算して、結果を `results/` に保存できます。

## できること

- `電車` の場合
  - 駅すぱあと Web サービスの経路検索 API を使って CO2 排出量を取得
- `車` の場合
  - 国土地理院の住所検索 API で緯度経度を取得
  - 国土地理院の距離計算 API で 2 点間距離を取得
  - `距離(km) × 車の CO2 排出量(g/km)` で CO2 を計算
- GUI 上で一覧表示、行編集、行追加、行削除
- `Treeview` の見出しクリックでソート
- 実行ログをコンソールに整形表示

## 画面イメージ

- 上部
  - `CSVを開く`
  - `全件を計算`
  - `保存`
  - `車 g/km` の調整欄
- 中央
  - 通勤データ一覧
- 下部
  - 選択行の編集フォーム

## CSV 形式

入力 CSV は以下の列を想定しています。

```csv
mode,from,to,co2
電車,船橋,品川,
車,東京都八王子市旭町1-1,東京都港区港南2-18-1,
```

各列の意味:

- `mode`
  - `電車` または `車`
  - 旧データの `train` / `car` も読み込み時に吸収します
- `from`
  - 出発地
  - `電車` なら駅名、`車` なら住所を入れる想定です
- `to`
  - 到着地
  - `電車` なら駅名、`車` なら住所を入れる想定です
- `co2`
  - 計算結果を入れる列
  - 初期状態では空欄で問題ありません

サンプルデータは [`data/sample.csv`](/mnt/d/projects/experimentals/eki-co2/data/sample.csv) にあります。

## ディレクトリ構成

```text
.
├── data/
│   └── sample.csv
├── results/
├── gui.py
├── lat_lon.py
├── main.py
├── main2.py
└── 通勤経路.xlsx
```

補足:

- `data/`
  - 入力用 CSV を置く場所
  - `sample.csv` 以外は `.gitignore` 対象です
- `results/`
  - GUI の保存先
  - すべて `.gitignore` 対象です

## セットアップ

前提:

- Python 3.14 系で確認
- `tkinter` が使える Python 環境
- 駅すぱあと API キー

### 1. 仮想環境を作る

このリポジトリでは `uv` 前提で `.venv-linux` を使っています。

```bash
uv venv .venv-linux
```

### 2. 必要ライブラリを入れる

```bash
uv pip install --python .venv-linux/bin/python requests python-dotenv openpyxl
```

`tkinter` は通常 Python に同梱ですが、環境によっては別途 OS 側の導入が必要です。

### 3. `.env` を置く

ルートに `.env` を作り、駅すぱあと API キーを設定します。

```env
EKISPERT_API_KEY=your_api_key_here
```

## 使い方

### GUI を起動する

```bash
./.venv-linux/bin/python gui.py
```

起動時に [`data/sample.csv`](/mnt/d/projects/experimentals/eki-co2/data/sample.csv) があれば自動で読み込みます。

### GUI の基本操作

1. `CSVを開く` で `data/` 内の CSV を読み込む
2. 必要なら下部フォームで行を編集する
3. `車 g/km` を調整する
4. `全件を計算` を押す
5. `保存` を押す

保存すると `results/` にタイムスタンプ付き CSV を出力します。

## コンソールログ

`全件を計算` 実行時は、どの API を使ったか分かるようにコンソールへ整形ログを出します。

```text
 1/12 | [電車] | 駅すぱあと   | 船橋               | 品川               |   510g
 3/12 | [ 車 ] | 距離測定     | 千葉県船橋市本... | 東京都港区港南... |  2808g
```

## 既存スクリプト

### [`main.py`](/mnt/d/projects/experimentals/eki-co2/main.py)

駅名ペアをコード内に直接書いて、駅すぱあと API から CO2 を取得する最小サンプルです。

### [`main2.py`](/mnt/d/projects/experimentals/eki-co2/main2.py)

[`通勤経路.xlsx`](/mnt/d/projects/experimentals/eki-co2/通勤経路.xlsx) を読み、検索用駅名列を使って CO2 を計算し、Excel に書き戻すスクリプトです。

### [`lat_lon.py`](/mnt/d/projects/experimentals/eki-co2/lat_lon.py)

国土地理院 API を使った住所ジオコーディングと距離計算の試作スクリプトです。

## 注意点

- `車` の CO2 は実走行距離ではなく、2 点間の距離計算 API ベースです
- そのため道路形状、渋滞、高速利用などは反映しません
- `車 g/km` は仮置きの係数です
- 実務用途というより、比較デモ・試作寄りのアプリです

## 今後の改善候補

- `車` の距離を道路距離ベースにする
- GUI 上でフィルタリングや複合ソートを入れる
- 比較結果の可視化を追加する
- 電車/車のペア比較を見やすくする
