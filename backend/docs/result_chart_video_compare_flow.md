# result_chart.html 動画比較機能のデータ受け渡し

## 全体像

`result_chart.html` の動画比較機能では、HTMLに分析データを直接埋め込まず、JavaScriptからFlask APIを呼び出してJSONを受け取ります。

```text
main_process.analyze()
  ↓
output_df / shap_importance_df_output が route.py のグローバル変数に入る
  ↓
result_chart.html が表示される
  ↓
JavaScript が Flask API を fetch() で呼ぶ
  ↓
JSON を受け取って select や Chart.js に渡す
```

## 1. 分析実行時にデータが作られる

`/run` で `analyze` モードを選ぶと、`backend/apps/route.py` の `run_process()` が動きます。

```python
shap_importance_df_output, scatter_df, ..., output_df, ... = main_process.analyze()
```

動画比較で主に使うデータは次の2つです。

```python
output_df
shap_importance_df_output
```

`output_df` には、動画ごとの分析済みデータが入っています。

```text
video_id
title
viewCount
strong_transcript_score
strong_comment_score
各特徴量...
```

`shap_importance_df_output` には、SHAP重要度の高い特徴量一覧が入っています。

```text
feature
importance
```

## 2. result_chart.html が表示される

分析後、`/result` にリダイレクトされます。

```python
return render_template("result_chart.html", feature_labels=feature_labels)
```

ただし、この時点で `output_df` の中身をHTMLへ全部渡しているわけではありません。

動画比較部分は、HTML表示後にJavaScriptからAPIを呼んで取得します。

## 3. 動画タイトルの選択肢を取得する

`result_chart.html` の読み込み時に、次の関数が動きます。

```javascript
loadCompareVideoOptions();
```

中ではFlask APIを呼びます。

```javascript
const response = await fetch("/api/analyze_videos/");
const videos = await response.json();
```

`/api/analyze_videos/` は `backend/apps/route.py` にあります。

```python
@app.route("/api/analyze_videos/", methods=["GET"])
def analyze_videos():
    df = output_df.copy()
```

`output_df` から `video_id` と `title` を取り出して、JSONで返します。

```json
{
  "video_id": "...",
  "title": "..."
}
```

フロント側では、そのJSONを `<select>` に入れています。

```javascript
const option = document.createElement("option");
option.value = video.video_id;
option.textContent = video.title;
select.appendChild(option);
```

選択欄の表示名は `title`、内部で送る値は `video_id` です。

## 4. ボタンを押すと選択した video_id を送る

「選択した動画を比較」ボタンを押すと、次の関数が動きます。

```javascript
compareSelectedVideos()
```

選択された動画IDを集めます。

```javascript
const selectedIds = Array.from(select.selectedOptions)
    .map(option => option.value);
```

例えば2本選ぶと、次のような配列になります。

```javascript
["abc123", "def456"]
```

それをURLパラメータにしてAPIへ送ります。

```javascript
const params = new URLSearchParams();
selectedIds.forEach(videoId => params.append("video_id", videoId));
params.append("top_n", "15");

const response = await fetch(`/api/analyze_result/?${params.toString()}`);
```

実際のURLは次のような形です。

```text
/api/analyze_result/?video_id=abc123&video_id=def456&top_n=15
```

## 5. analyze_result が比較用データを作る

`backend/apps/route.py` の `analyze_result()` がリクエストを受け取ります。

```python
selected_ids = request.args.getlist("video_id")
```

ここで複数の `video_id` をリストとして受け取ります。

```python
["abc123", "def456"]
```

次に `output_df` から、中央値行と動画行を分けます。

```python
raw_df = output_df.copy()
median_mask = raw_df["video_id"].isin(["中央値", "荳ｭ螟ｮ蛟､"])
median_df = raw_df[median_mask]
df = raw_df[~median_mask].copy()
```

`median_df` は「中央値比」の基準になります。

`df` は実際の動画データです。

## 6. buzz_type を計算する

`strong_transcript_score` と `strong_comment_score` の上位25%ラインを計算します。

```python
transcript_threshold = df["strong_transcript_score"].quantile(0.75)
comments_threshold = df["strong_comment_score"].quantile(0.75)
```

そして各動画に `buzz_type` を付けます。

```python
df["buzz_type"] = df.apply(
    classify,
    args=(transcript_threshold, comments_threshold),
    axis=1
)
```

`classify()` は、字幕側とコメント側のバズ単語スコアが高いかどうかで4分類します。

## 7. 表示する特徴量をSHAP上位に絞る

全特徴量を出すと多すぎるため、`shap_importance_df_output` の上位から最大15個に絞ります。

```python
for _, row in shap_importance_df_output.head(top_n).iterrows():
    feature_name = row["feature"]
```

SHAP側の特徴量名は日本語ラベル化されている場合があります。

そのため、`FEATURE_LABELS` を逆引きして、`output_df` の元カラム名に戻します。

```python
raw_feature_name = REVERSE_FEATURE_LABELS.get(feature_name, feature_name)
```

最終的に、比較対象の特徴量は次のように決まります。

```python
feature_cols = shap_feature_cols or feature_cols[:top_n]
```

## 8. 各動画について中央値比を作る

選択された動画だけに絞ります。

```python
selected_df = df[df["video_id"].isin(selected_ids)].copy()
```

そして、特徴量ごとに次の情報を作ります。

```python
{
    "feature": 表示用特徴量名,
    "raw_feature": 元のカラム名,
    "value": 動画の値,
    "median": 中央値,
    "diff": 動画の値 - 中央値,
    "ratio": 動画の値 / 中央値
}
```

この `ratio` が横棒グラフの値になります。

例えば次のデータがあるとします。

```json
{
  "feature": "コメント感情スコア",
  "value": 120,
  "median": 60,
  "ratio": 2.0
}
```

これは「この動画は中央値の2倍」という意味です。

API全体としては、次のようなJSONを返します。

```json
{
  "features": ["特徴量A", "特徴量B"],
  "videos": [
    {
      "video_id": "abc123",
      "title": "動画タイトル",
      "view_count": 1234567,
      "buzz_type": "本物バズ",
      "comparisons": [
        {
          "feature": "特徴量A",
          "value": 10,
          "median": 5,
          "diff": 5,
          "ratio": 2.0
        }
      ]
    }
  ]
}
```

## 9. result_chart.html がグラフを描く

フロント側では、返ってきた `videos` を1件ずつ処理します。

```javascript
result.videos.forEach((video, index) => {
```

動画ごとにカードを作ります。

```javascript
const title = document.createElement("h3");
title.textContent = video.title;
```

再生数も表示します。

```javascript
viewCount.textContent = `再生数: ${formattedViewCount}`;
```

`buzz_type` も表示します。

```javascript
buzzType.textContent = `buzz_type: ${video.buzz_type}`;
```

最後に、`comparisons` の `ratio` をChart.jsに渡します。

```javascript
const labels = comparisons.map(item => item.feature);
const ratios = comparisons.map(item => Number(item.ratio.toFixed(2)));
```

そして横棒グラフを作ります。

```javascript
new Chart(canvas, {
    type: "bar",
    data: {
        labels: labels,
        datasets: [{
            label: "中央値比",
            data: ratios
        }]
    },
    options: {
        indexAxis: "y"
    }
});
```

グラフのY軸が特徴量名、X軸が中央値比です。

```text
特徴量A | ======== 2.0
特徴量B | ====     1.0
特徴量C | ==       0.5
```

## まとめ

```text
selectで選んだ video_id
  ↓ fetchでFlaskへ送る
route.py の analyze_result()
  ↓ output_df から該当動画を探す
  ↓ shap_importance_df_output で表示特徴量を絞る
  ↓ 各特徴量の value / median を計算
JSONで返す
  ↓
result_chart.html が Chart.js で棒グラフ化
```

`result_chart.html` は直接 `output_df` を持っていません。

必要なタイミングで `/api/analyze_videos/` と `/api/analyze_result/` に問い合わせて、JSONとして受け取っています。
