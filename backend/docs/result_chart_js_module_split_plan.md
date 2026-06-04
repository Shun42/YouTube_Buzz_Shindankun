# result_chart.html のグラフ描画処理を JS ファイルへ分離する方針

## 全体像

`result_chart.html` が煩雑になっている主な理由は、1つのHTML内に次の責務が混在しているためです。

```text
HTML
  ↓
canvas / select / button などの表示要素を置く
  ↓
script内で API fetch / データ加工 / Chart.js描画 / イベント登録 をすべて行う
```

今後は、`main_process.py` が処理を関数として分けているのと同じように、グラフ描画用の JavaScript を別ファイルへ分離します。

```text
result_chart.html
  ↓
画面に必要な canvas / select / button だけを持つ
  ↓
frontend/static/js/result_chart.js を読み込む
  ↓
result_chart.js 側で fetch / データ加工 / Chart.js描画 / イベント登録を行う
```

Flask 側ではすでに `frontend/static` が static 配信先になっています。

```python
flaskapp = Flask(
    __name__,
    template_folder="../../frontend/templates",
    static_folder="../../frontend/static",
)
```

そのため、JSファイルは次の場所に置くのが自然です。

```text
frontend/static/js/result_chart.js
```

## 1. 最初に分離する範囲

いきなり全グラフを一度に分離すると確認が大変になるため、まずは1つのグラフだけを移すのがおすすめです。

最初の対象としては、依存が少ない `SHAPChart` が向いています。

```text
result_chart.html 内の createSHAPChart()
  ↓
frontend/static/js/result_chart.js へ移動
```

理由は次の通りです。

```text
select変更イベントがない
canvas が1つだけ
API が /api/shap だけ
Chart.js の bar chart だけ
```

この小さい単位で成功させてから、散布図、時系列、ワードクラウド、strong_words、動画比較へ広げると安全です。

## 2. ディレクトリを作る

まず `frontend/static/js` を作ります。

```text
frontend/
  static/
    js/
      result_chart.js
  templates/
    result_chart.html
```

既に `frontend/static` は存在しているため、追加するのは `js` ディレクトリと `result_chart.js` です。

## 3. result_chart.html から JS を読み込む

`result_chart.html` の末尾、`</body>` の直前あたりで外部JSを読み込みます。

```html
<script src="{{ url_for('static', filename='js/result_chart.js') }}"></script>
</body>
```

Chart.js本体やプラグインは、`result_chart.js` より前に読み込まれている必要があります。

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-chart-wordcloud@4.4.5/build/index.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation"></script>

<!-- 自作JSは最後に読む -->
<script src="{{ url_for('static', filename='js/result_chart.js') }}"></script>
```

読み込み順は重要です。

```text
Chart.js
  ↓
Chart.js plugin
  ↓
自作の result_chart.js
```

## 4. JSファイル側に初期化関数を作る

外部JSでは、ページ読み込み後に初期化関数を呼ぶ形にします。

```javascript
document.addEventListener("DOMContentLoaded", () => {
    initResultCharts();
});

function initResultCharts() {
    createSHAPChart();
}
```

この形にしておくと、あとからグラフを追加するときも `initResultCharts()` に追記するだけで済みます。

```javascript
function initResultCharts() {
    createSHAPChart();
    createScatterChart(defaultFeature);
    createTimelineChart();
    createWordCloudChart();
    createStrongWordsScatter();
    loadCompareVideoOptions();
}
```

## 5. グラフインスタンスはJSファイル内で管理する

現在の `result_chart.html` では、次のような変数がHTML内にあります。

```javascript
let chart_one;
let chart_two;
let chart_three;
```

分離後は、これらも `result_chart.js` 側へ移します。

ただし、`chart_one`, `chart_two` のような番号名は増えるほど読みづらくなるため、分離のタイミングで意味のある名前に変えると後で楽です。

```javascript
let shapChart;
let scatterHighChart;
let scatterLowChart;
let timelineBuzzChart;
let timelineNonBuzzChart;
let wordCloudCommentChart;
let wordCloudTagChart;
let wordCloudWordChart;
let strongWordsScatterChart;
let comparisonCharts = [];
```

どの変数がどのグラフを指すか分かるようになります。

## 6. SHAPグラフの分離例

`result_chart.js` に次のような関数を置きます。

```javascript
let shapChart;

async function createSHAPChart() {
    const response = await fetch("/api/shap");
    const shapData = await response.json();

    const labels = shapData.map(item => item.feature);
    const importances = shapData.map(item => item.importance);
    const canvas = document.getElementById("SHAPChart");

    if (!canvas) {
        return;
    }

    if (shapChart) {
        shapChart.destroy();
    }

    shapChart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "SHAP値",
                data: importances
            }]
        },
        options: {
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "特徴量"
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: "SHAP値"
                    }
                }
            }
        }
    });
}
```

ポイントは、HTMLから `createSHAPChart()` の中身を消して、JSファイルへそのまま移すことです。

HTML側には canvas だけ残します。

```html
<canvas id="SHAPChart"></canvas>
```

## 7. HTMLから消してよいもの、残すもの

分離後の `result_chart.html` に残すものは、基本的に表示の骨組みだけです。

残すもの:

```text
h1 / h2 などの見出し
canvas
select
button
div
CSS
Chart.js CDNの読み込み
自作JSの読み込み
```

JSファイルへ移すもの:

```text
let chart_xxx
fetch()
response.json()
Chart.js の new Chart(...)
グラフ用のデータ加工
addEventListener()
createElement()
```

最終的なイメージは次のようになります。

```html
<canvas id="SHAPChart"></canvas>

<select id="featureSelect">
    {% for feature in feature_labels %}
    <option value="{{ feature }}">{{ feature }}</option>
    {% endfor %}
</select>

<canvas id="scatterChartHigh"></canvas>
<canvas id="scatterChartLow"></canvas>

<script src="{{ url_for('static', filename='js/result_chart.js') }}"></script>
```

## 8. Jinjaで渡している値の扱い

`feature_labels` は現在、HTML内の `<select>` を作るために使われています。

```html
{% for feature in feature_labels %}
<option value="{{ feature }}">{{ feature }}</option>
{% endfor %}
```

この部分は、最初はHTMLに残してよいです。

理由は、Jinjaの変数は通常の `.js` ファイル内では直接使えないためです。

```text
result_chart.html
  → Jinjaが処理するので {{ feature_labels }} が使える

frontend/static/js/result_chart.js
  → 静的ファイルなので {{ feature_labels }} は基本的に使わない
```

JSファイル側では、HTML上に作られた `select` から現在値を読み取れば十分です。

```javascript
const featureSelect = document.getElementById("featureSelect");
const selectedFeature = featureSelect.value;
createScatterChart(selectedFeature);
```

もし将来的にJS側へ初期データを渡したくなった場合は、HTMLに `data-*` 属性として埋め込む方法があります。

```html
<body data-default-feature="{{ feature_labels[0] }}">
```

JS側では次のように読みます。

```javascript
const defaultFeature = document.body.dataset.defaultFeature;
```

ただし、最初の分離ではここまでしなくても問題ありません。

## 9. 散布図を分離するときの考え方

散布図は `featureSelect` の変更イベントとつながっています。

HTMLに残すもの:

```html
<select id="featureSelect">
    {% for feature in feature_labels %}
    <option value="{{ feature }}">{{ feature }}</option>
    {% endfor %}
</select>

<canvas id="scatterChartHigh"></canvas>
<canvas id="scatterChartLow"></canvas>
```

JSへ移すもの:

```javascript
let scatterHighChart;
let scatterLowChart;

async function createScatterChart(feature) {
    ...
}

function setupScatterChartEvents() {
    const featureSelect = document.getElementById("featureSelect");

    if (!featureSelect) {
        return;
    }

    featureSelect.addEventListener("change", () => {
        createScatterChart(featureSelect.value);
    });

    createScatterChart(featureSelect.value);
}
```

`initResultCharts()` からは次のように呼びます。

```javascript
function initResultCharts() {
    createSHAPChart();
    setupScatterChartEvents();
}
```

現在は初期値として固定文字列を渡しています。

```javascript
createscatterChart("コメント数");
```

分離後は、`select` の先頭または現在選択中の値を使う方が保守しやすいです。

```javascript
createScatterChart(featureSelect.value);
```

## 10. 共通処理を小さく関数化する

外部JSへ分離したあと、似た処理が見えてきたら共通関数にします。

例えば、APIからJSONを取る処理です。

```javascript
async function fetchJson(url) {
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`API request failed: ${url}`);
    }

    return response.json();
}
```

すると各グラフでは次のように書けます。

```javascript
const shapData = await fetchJson("/api/shap");
```

Chart.js の破棄も共通化できます。

```javascript
function destroyChart(chart) {
    if (chart) {
        chart.destroy();
    }
}
```

ただし、最初から共通化しすぎる必要はありません。

おすすめの順番は次の通りです。

```text
1. まずそのままJSファイルへ移す
2. 動くことを確認する
3. 重複が目立つところだけ共通関数にする
```

## 11. ファイルを分ける場合の発展形

最初は `result_chart.js` 1ファイルで十分です。

```text
frontend/static/js/result_chart.js
```

グラフがさらに増えたり、1ファイルが長くなった場合は、次のように分割できます。

```text
frontend/static/js/result_chart/
  api.js
  shap_chart.js
  scatter_chart.js
  timeline_chart.js
  wordcloud_chart.js
  strong_words_chart.js
  compare_chart.js
  index.js
```

ただし、ブラウザで ES modules を使う場合は読み込み方が変わります。

```html
<script type="module" src="{{ url_for('static', filename='js/result_chart/index.js') }}"></script>
```

`index.js` では各ファイルを import します。

```javascript
import { createSHAPChart } from "./shap_chart.js";
import { setupScatterChartEvents } from "./scatter_chart.js";

document.addEventListener("DOMContentLoaded", () => {
    createSHAPChart();
    setupScatterChartEvents();
});
```

ただ、最初からこの形にすると変更箇所が増えます。

今回の段階では、まずは次の構成がおすすめです。

```text
frontend/static/js/result_chart.js
```

## 12. 移行のおすすめ順序

実装するときは、次の順番で進めると確認しやすいです。

```text
1. frontend/static/js/result_chart.js を作る
2. result_chart.html の末尾で result_chart.js を読み込む
3. SHAPグラフの let 変数と createSHAPChart() だけをJSへ移す
4. SHAPグラフが表示されるか確認する
5. 散布図をJSへ移す
6. featureSelect の change イベントもJSへ移す
7. 時系列グラフをJSへ移す
8. ワードクラウドをJSへ移す
9. strong_words散布図をJSへ移す
10. 動画比較機能をJSへ移す
11. HTML内に残った script タグを削除する
12. 似た処理を共通関数へまとめる
```

1つ移すたびに画面を確認するのが大事です。

```text
移す
  ↓
画面を開く
  ↓
ブラウザの開発者ツール Console を確認する
  ↓
グラフが出ることを確認する
  ↓
次のグラフへ進む
```

## 13. 動画比較機能を分離するときの注意

動画比較機能は、ほかのグラフより少し責務が多いです。

```text
動画一覧をAPIから取得する
selectにoptionを追加する
選択されたvideo_idを集める
比較APIへ送る
結果カードをDOM生成する
カード内にcanvasを作る
Chart.jsで比較グラフを描く
古い比較グラフをdestroyする
```

そのため、次のように関数を分けると読みやすくなります。

```javascript
let comparisonCharts = [];

async function loadCompareVideoOptions() {
    ...
}

function destroyComparisonCharts() {
    ...
}

function createMedianRatioChart(canvas, video) {
    ...
}

function renderComparisonResult(video, index, resultsElement) {
    ...
}

async function compareSelectedVideos() {
    ...
}

function setupCompareVideoEvents() {
    const button = document.getElementById("compareVideosButton");

    if (!button) {
        return;
    }

    button.addEventListener("click", compareSelectedVideos);
    loadCompareVideoOptions();
}
```

`initResultCharts()` からは次のように呼びます。

```javascript
function initResultCharts() {
    createSHAPChart();
    setupScatterChartEvents();
    createTimelineChart();
    createWordCloudChart();
    createStrongWordsScatter();
    setupCompareVideoEvents();
}
```

## 14. 途中でエラーになりやすいポイント

よくあるエラーは次の通りです。

```text
Chart is not defined
```

原因は、自作JSより前に Chart.js が読み込まれていないことです。

```text
Cannot read properties of null
```

原因は、`document.getElementById(...)` で対象IDの要素が見つかっていないことです。

対策として、JS側では要素が存在するか確認してから処理します。

```javascript
const canvas = document.getElementById("SHAPChart");

if (!canvas) {
    return;
}
```

```text
404 result_chart.js
```

原因は、JSファイルの置き場所か `url_for` の指定が違うことです。

正しい例です。

```text
frontend/static/js/result_chart.js
```

```html
<script src="{{ url_for('static', filename='js/result_chart.js') }}"></script>
```

## 15. 最終的な完成イメージ

`result_chart.html` は、表示構造を持つファイルになります。

```text
result_chart.html
  ↓
見出し
select
button
canvas
CSS
script読み込み
```

`result_chart.js` は、画面の動きを持つファイルになります。

```text
result_chart.js
  ↓
API呼び出し
データ加工
Chart.js描画
イベント登録
グラフ破棄
DOM生成
```

まとめると、責務は次のように分けます。

```text
backend/apps/route.py
  ↓
Flask APIとしてJSONを返す

frontend/templates/result_chart.html
  ↓
グラフを表示するためのHTML要素を置く

frontend/static/js/result_chart.js
  ↓
APIからJSONを取得してChart.jsで描画する
```

この形にすると、今後グラフを追加するときも `result_chart.html` に長い `<script>` を増やさずに済みます。

