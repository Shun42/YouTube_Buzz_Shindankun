# React_study.js 解説書

この Markdown は、`React_study.js` を読みながら React の考え方を学習するための解説です。

元の `result_chart.html` は、HTML の中に `canvas` や `select` を置き、`script` タグ内で `document.getElementById()`、`fetch()`、`new Chart()` を直接呼び出していました。

`React_study.js` では、それを React の考え方に合わせて次のように分けています。

```text
画面のまとまり
  -> React コンポーネント

画面の状態
  -> useState

API 取得や Chart.js 描画
  -> useEffect

canvas や Chart.js インスタンス
  -> useRef

配列データから option やカードを作る処理
  -> map
```

## 注意点

このファイルは JSX で書かれています。

JSX はブラウザがそのまま実行できる JavaScript ではありません。実際に動かすには、Vite、React Scripts、Babel などで JavaScript に変換する必要があります。

```jsx
ReactDOM.createRoot(rootElement).render(<ResultChartApp />);
```

このような `<ResultChartApp />` の書き方が JSX です。

## 全体構成

主な関数とコンポーネントは次の通りです。

| 名前 | 役割 |
|---|---|
| `fetchJson` | API から JSON を取得する共通関数 |
| `destroyChart` | Chart.js の古いグラフを破棄する共通関数 |
| `createWordCloudSizes` | ワードクラウド用の文字サイズを作る |
| `linearRegression` | 散布図の回帰直線を計算する |
| `Section` | 見出し付きの画面ブロック |
| `ChartBox` | グラフ表示用の高さを持つ箱 |
| `ShapChart` | SHAP の棒グラフ |
| `ScatterSection` | 特徴量選択と散布図 2 つをまとめる |
| `ScatterChart` | バズ動画 / 非バズ動画の散布図 |
| `TimelineChart` | 動画時間ごとの盛り上がり折れ線グラフ |
| `WordCloudChart` | ワードクラウド |
| `StrongWordsScatter` | strong_words の分類散布図 |
| `MedianRatioChart` | 動画比較の中央値比グラフ |
| `VideoComparison` | 動画選択と比較結果表示 |
| `ResultChartApp` | 画面全体を組み立てる親コンポーネント |

## React の基本パターン

### コンポーネント

React では、画面の部品を関数として作ります。

```jsx
function Section({ title, children }) {
  return (
    <section>
      <h2>{title}</h2>
      {children}
    </section>
  );
}
```

この例では、`title` と `children` を受け取って、見出し付きのセクションを返しています。

使う側はこのように書けます。

```jsx
<Section title="SHAPグラフ">
  <p>どの特徴量がバズに関係しているかを表示します。</p>
</Section>
```

HTML に似ていますが、これは JavaScript の中に書く JSX です。

### props

親コンポーネントから子コンポーネントへ渡す値を props と呼びます。

```jsx
<TimelineChart buzzLevel="buzz" />
```

受け取る側はこうです。

```jsx
function TimelineChart({ buzzLevel }) {
  ...
}
```

`buzzLevel` に `"buzz"` が入るので、API の URL を切り替えられます。

### useState

`useState` は、画面上で変わる値を保持します。

```jsx
const [selectedFeature, setSelectedFeature] = useState("");
```

この例では、散布図で選択中の特徴量を `selectedFeature` として持っています。

値を変えるときは、直接代入ではなく `setSelectedFeature(...)` を使います。

```jsx
onChange={(event) => setSelectedFeature(event.target.value)}
```

React では state が変わると、その state を使っている画面が再描画されます。

### useEffect

`useEffect` は、React の描画とは別に行う処理を書く場所です。

このファイルでは主に次の用途で使っています。

- API からデータを取得する
- Chart.js で canvas にグラフを描く
- コンポーネントが消えるときにグラフを破棄する

基本形は次の通りです。

```jsx
useEffect(() => {
  async function draw() {
    const data = await fetchJson("/api/shap");
    ...
  }

  draw().catch(console.error);

  return () => {
    destroyChart(chartRef);
  };
}, []);
```

最後の `[]` は依存配列です。

依存配列に入れた値が変わると、`useEffect` の中身がもう一度実行されます。

### useRef

`useRef` は、再描画されても値を保持したいときに使います。

このファイルでは 2 種類の用途があります。

```jsx
const canvasRef = useRef(null);
const chartRef = useRef(null);
```

`canvasRef` は JSX の `canvas` 要素を参照するために使います。

```jsx
<canvas ref={canvasRef} />
```

`chartRef` は Chart.js のインスタンスを保持するために使います。

```jsx
chartRef.current = new Chart(canvasRef.current, {...});
```

React の state に Chart.js インスタンスを入れる必要はありません。Chart.js インスタンスは画面表示の状態というより、外部ライブラリの管理対象だからです。

## Chart.js と React の関係

React は JSX で `canvas` を表示します。

しかし、Chart.js が実際にグラフを描くのは `canvas` の中です。

そのため、このファイルでは次の流れにしています。

```text
1. JSX で <canvas ref={canvasRef} /> を返す
2. 画面に canvas が作られる
3. useEffect が実行される
4. canvasRef.current を Chart.js に渡す
5. new Chart(...) でグラフを描く
```

例:

```jsx
return (
  <ChartBox>
    <canvas ref={canvasRef} />
  </ChartBox>
);
```

```jsx
chartRef.current = new Chart(canvasRef.current, {
  type: "bar",
  data: {...},
  options: {...},
});
```

重要なのは、再描画時に古い Chart.js インスタンスを破棄することです。

```jsx
destroyChart(chartRef);
```

これをしないと、同じ canvas に複数のグラフが重なったり、メモリが残ったりします。

## 各コンポーネントの解説

### ResultChartApp

`ResultChartApp` は一番親のコンポーネントです。

この中で、画面全体の順番を決めています。

```jsx
function ResultChartApp() {
  return (
    <main>
      <Section title="SHAPグラフ">
        <ShapChart onFeaturesLoaded={handleFeaturesLoaded} />
      </Section>

      <ScatterSection featureOptions={featureOptions} />
      ...
      <VideoComparison />
    </main>
  );
}
```

見るポイントは、細かいグラフ描画の処理がここには書かれていないことです。

親コンポーネントは「画面の並び」を担当し、個別のグラフ処理は子コンポーネントに任せています。

### ShapChart

`ShapChart` は `/api/shap` からデータを取得して、棒グラフを描きます。

流れは次の通りです。

```text
1. /api/shap を fetch
2. feature を labels にする
3. importance を data にする
4. Chart.js の bar chart を作る
5. feature の一覧を親へ渡す
```

親へ渡している部分はこちらです。

```jsx
onFeaturesLoaded(labels);
```

これは散布図のセレクトボックス候補を作るために使われています。

### ScatterSection

`ScatterSection` は、特徴量選択の `select` と 2 つの散布図をまとめています。

```jsx
const [selectedFeature, setSelectedFeature] = useState("");
```

選択中の特徴量を state として持ちます。

```jsx
<select
  value={selectedFeature}
  onChange={(event) => setSelectedFeature(event.target.value)}
>
```

選ばれた特徴量は、2 つの `ScatterChart` に props として渡されます。

```jsx
<ScatterChart feature={selectedFeature} buzzLevel="highbuzz" />
<ScatterChart feature={selectedFeature} buzzLevel="lowbuzz" />
```

これにより、同じ `ScatterChart` コンポーネントを使い回しながら、バズ動画と非バズ動画のグラフを描けます。

### ScatterChart

`ScatterChart` は、選択された特徴量に応じて API を呼びます。

```jsx
const encodedFeature = encodeURIComponent(feature);
const points = await fetchJson(`/api/scatter/${buzzLevel}/${encodedFeature}`);
```

`buzzLevel` によって API が変わります。

```text
highbuzz -> /api/scatter/highbuzz/...
lowbuzz  -> /api/scatter/lowbuzz/...
```

また、散布図だけでなく回帰直線も一緒に描いています。

```jsx
{
  type: "line",
  label: `回帰直線(${title})`,
  data: regressionLine(points),
}
```

### TimelineChart

`TimelineChart` は動画の時間ごとの盛り上がりを折れ線グラフで描きます。

```jsx
<TimelineChart buzzLevel="buzz" />
<TimelineChart buzzLevel="nonbuzz" />
```

`buzzLevel` を変えることで、同じコンポーネントを 2 回使っています。

React では、このように props を変えて同じ部品を再利用することが多いです。

### WordCloudChart

`WordCloudChart` は、コメント、タグ、タイトルのワードクラウドを描く共通コンポーネントです。

```jsx
<WordCloudChart
  endpoint="/api/wordcloud/comment/"
  label="ワードクラウド(コメント頻出語)"
  maxSize={40}
/>
```

変わる部分だけ props で渡しています。

| props | 意味 |
|---|---|
| `endpoint` | データを取得する API |
| `label` | Chart.js のラベル |
| `maxSize` | ワードクラウドの最大文字サイズ |

`createWordCloudSizes` は、単語の出現数を文字サイズに変換しています。

### StrongWordsScatter

`StrongWordsScatter` は `/api/strong_words_scatter/` の結果を分類ごとにまとめて散布図にします。

ポイントは、API から来た配列を `buzz_type` ごとにグループ化しているところです。

```jsx
const groupedData = {};

rawData.forEach((item) => {
  if (!groupedData[item.buzz_type]) {
    groupedData[item.buzz_type] = [];
  }

  groupedData[item.buzz_type].push(item);
});
```

その後、`Object.keys(groupedData).map(...)` で Chart.js の dataset を作っています。

```jsx
datasets: Object.keys(groupedData).map((type) => ({
  label: type,
  data: groupedData[type],
  backgroundColor: BUZZ_TYPE_COLORS[type],
}))
```

### VideoComparison

`VideoComparison` は動画比較機能を担当します。

このコンポーネントは state が多めです。

```jsx
const [videos, setVideos] = useState([]);
const [selectedIds, setSelectedIds] = useState([]);
const [status, setStatus] = useState("");
const [comparisonVideos, setComparisonVideos] = useState([]);
```

| state | 役割 |
|---|---|
| `videos` | セレクトボックスに表示する動画一覧 |
| `selectedIds` | 選択中の動画 ID |
| `status` | 読み込み中やエラーメッセージ用の文字列 |
| `comparisonVideos` | 比較結果として表示する動画データ |

最初に動画一覧を取得する処理は `useEffect` にあります。

```jsx
useEffect(() => {
  async function loadOptions() {
    const options = await fetchJson("/api/analyze_videos/");
    setVideos(options);
  }

  loadOptions().catch(console.error);
}, []);
```

比較ボタンを押したときは `compareSelectedVideos` が実行されます。

```jsx
<button onClick={() => {
  compareSelectedVideos().catch(console.error);
}}>
  選択した動画を比較
</button>
```

比較結果は `comparisonVideos.map(...)` でカードのように表示しています。

```jsx
{comparisonVideos.map((video) => (
  <section key={video.video_id}>
    <h3>{video.title}</h3>
    <MedianRatioChart video={video} />
  </section>
))}
```

### MedianRatioChart

`MedianRatioChart` は、動画ごとの特徴量が中央値と比べてどれくらい大きいかを棒グラフにします。

`video.comparisons` の中から `ratio` があるものだけを使います。

```jsx
const comparisons = useMemo(
  () => video.comparisons.filter((item) => item.ratio !== null),
  [video.comparisons]
);
```

`useMemo` は計算結果を覚えておくための hook です。

この例では、`video.comparisons` が変わったときだけ filter をやり直します。

## JSX の読み方

### JavaScript の値を表示する

JSX の中で JavaScript の値を使うときは `{}` を使います。

```jsx
<h3>{video.title}</h3>
```

### 条件付き表示

`status` があるときだけ `<p>` を表示しています。

```jsx
{status && <p>{status}</p>}
```

これは次の意味です。

```text
status が空ではない -> <p>{status}</p> を表示
status が空           -> 何も表示しない
```

### 配列から画面を作る

React では、配列を `map` して JSX を作ることがよくあります。

```jsx
{videos.map((video) => (
  <option key={video.video_id} value={video.video_id}>
    {video.title}
  </option>
))}
```

`key` は React がリスト項目を識別するために必要です。

## result_chart.html との対応

元の HTML では、おおよそ次のような書き方でした。

```javascript
const response = await fetch("/api/shap");
const shapData = await response.json();
const ctx = document.getElementById("SHAPChart");
new Chart(ctx, {...});
```

React 版では、次のように分かれます。

```jsx
const canvasRef = useRef(null);

useEffect(() => {
  async function draw() {
    const shapData = await fetchJson("/api/shap");
    chartRef.current = new Chart(canvasRef.current, {...});
  }

  draw().catch(console.error);
}, []);

return <canvas ref={canvasRef} />;
```

大きな違いは、React では `document.getElementById()` を基本的に使わず、`ref` で DOM 要素にアクセスする点です。

## 学習するときのおすすめ順

1. `Section` と `ChartBox` を読む
2. `ResultChartApp` を読んで画面全体の構造を見る
3. `ShapChart` で `useEffect` と `useRef` の流れを見る
4. `ScatterSection` で `useState` と `onChange` を見る
5. `ScatterChart` で props が API 呼び出しに使われる流れを見る
6. `VideoComparison` で複数の state と `map` に慣れる
7. `MedianRatioChart` で `useMemo` を確認する

## このファイルで特に大事な React の考え方

React では、画面を「今の状態から作られる結果」として考えます。

例えば散布図では、選択中の特徴量が state です。

```jsx
const [selectedFeature, setSelectedFeature] = useState("");
```

この state が変わると、React は次の JSX をもう一度評価します。

```jsx
<ScatterChart feature={selectedFeature} buzzLevel="highbuzz" />
<ScatterChart feature={selectedFeature} buzzLevel="lowbuzz" />
```

そして `ScatterChart` 側の `useEffect` が、新しい `feature` を使って API を呼び直します。

```text
select を変更
  -> selectedFeature が変わる
  -> ScatterChart の props が変わる
  -> useEffect が再実行される
  -> 新しいグラフが描画される
```

この流れが React らしいデータの流れです。

## 実際に動かす場合の次のステップ

このファイルを実際に動かすには、React のビルド環境が必要です。

代表的には Vite を使う形です。

```text
frontend/
  src/
    React_study.jsx
  index.html
  package.json
```

その場合は、今のファイルを `.jsx` として置き、React と Chart.js を `import` する形に変えます。

```jsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import Chart from "chart.js/auto";
```

ただし、今回の `React_study.js` は「読むための 1 ファイル教材」として作っているので、まずはこのまま JSX の構造を追うのがおすすめです。
