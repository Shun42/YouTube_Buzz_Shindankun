/*
    result_chart.html を JSX 形式の React で書き直した学習用ファイルです。

    注意:
    JSX はブラウザがそのまま実行できる JavaScript ではありません。
    実際に動かすには Vite / React Scripts / Babel などで変換する必要があります。

    このファイルはプロジェクト本体に組み込むよりも、
    「HTML + DOM操作 + Chart.js」を React ではどう分けるかを読むための教材です。

    React の大事な見方:
    - return の中に JSX で画面を書く
    - useState で画面の状態を持つ
    - useEffect で API 読み込みや Chart.js 描画などの副作用を書く
    - useRef で canvas や Chart.js インスタンスを保持する
*/

const { useCallback, useEffect, useMemo, useRef, useState } = React;

const WORD_CLOUD_COLORS = [
    "#1b9e77",
    "#d95f02",
    "#7570b3",
    "#e7298a",
    "#66a61e",
    "#e6ab02",
    "#a6761d",
    "#1f78b4",
    "#b2df8a",
    "#fb9a99",
    "#fdbf6f",
    "#cab2d6",
];

const BUZZ_TYPE_COLORS = {
    "本物バズ": "rgba(255, 99, 132, 0.8)",
    "釣り・内容先行型": "rgba(255, 159, 64, 0.8)",
    "共感型": "rgba(54, 162, 235, 0.8)",
    "低反応型": "rgba(150, 150, 150, 0.6)",

    // 今のバックエンドが文字化けした分類名を返す場合の保険です。
    "譛ｬ迚ｩ繝舌ぜ": "rgba(255, 99, 132, 0.8)",
    "驥｣繧翫・蜀・ｮｹ蜈郁｡悟梛": "rgba(255, 159, 64, 0.8)",
    "蜈ｱ諢溷梛": "rgba(54, 162, 235, 0.8)",
    "菴主渚蠢懷梛": "rgba(150, 150, 150, 0.6)",
};

async function fetchJson(url) {
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`API request failed: ${url}`);
    }

    return response.json();
}

function destroyChart(chartRef) {
    if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
    }
}

function createWordCloudSizes(items, minSize = 12, maxSize = 42) {
    const counts = items.map((item) => Number(item.count) || 0);

    if (counts.length === 0) {
        return [];
    }

    const minCount = Math.min(...counts);
    const maxCount = Math.max(...counts);

    if (minCount === maxCount) {
        return counts.map(() => Math.round((minSize + maxSize) / 2));
    }

    const minRoot = Math.sqrt(minCount);
    const maxRoot = Math.sqrt(maxCount);

    return counts.map((count) => {
        const normalized = (Math.sqrt(count) - minRoot) / (maxRoot - minRoot);
        return Math.round(minSize + normalized * (maxSize - minSize));
    });
}

function linearRegression(points) {
    const n = points.length;

    if (n === 0) {
        return { a: 0, b: 0 };
    }

    const xTotal = points.reduce((sum, point) => sum + point.x, 0);
    const yTotal = points.reduce((sum, point) => sum + point.y, 0);
    const xxTotal = points.reduce((sum, point) => sum + point.x * point.x, 0);
    const xyTotal = points.reduce((sum, point) => sum + point.x * point.y, 0);
    const denominator = n * xxTotal - xTotal * xTotal;

    if (denominator === 0) {
        return { a: 0, b: yTotal / n };
    }

    return {
        a: (n * xyTotal - xTotal * yTotal) / denominator,
        b: (xxTotal * yTotal - xyTotal * xTotal) / denominator,
    };
}

function regressionLine(points) {
    const { a, b } = linearRegression(points);

    return points
        .map((point) => ({ x: point.x, y: a * point.x + b }))
        .sort((left, right) => left.x - right.x);
}

function Section({ title, children }) {
    return (
        <section style={{ marginBottom: "32px" }}>
        <h2>{title}</h2>
        {children}
        </section>
    );
}

function ChartBox({ children, tall = false }) {
    return (
        <div
        style={{
            width: "100%",
            height: tall ? "100vh" : "360px",
            marginBottom: "24px",
        }}
        >
        {children}
        </div>
    );
}

function ShapChart({ onFeaturesLoaded }) {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        let ignore = false;

        async function draw() {
        const shapData = await fetchJson("/api/shap");

        if (ignore || !canvasRef.current) {
            return;
        }

        const labels = shapData.map((item) => item.feature);
        const importances = shapData.map((item) => item.importance);

        onFeaturesLoaded(labels);
        destroyChart(chartRef);

        chartRef.current = new Chart(canvasRef.current, {
            type: "bar",
            data: {
            labels,
            datasets: [
                {
                label: "SHAP値",
                data: importances,
                },
            ],
            },
            options: {
            responsive: true,
            scales: {
                x: {
                title: {
                    display: true,
                    text: "特徴量",
                },
                },
                y: {
                title: {
                    display: true,
                    text: "SHAP値",
                },
                },
            },
            },
        });
        }

        draw().catch(console.error);

        return () => {
        ignore = true;
        destroyChart(chartRef);
        };
    }, [onFeaturesLoaded]);

    return (
        <ChartBox>
        <canvas ref={canvasRef} />
        </ChartBox>
    );
}

function ScatterChart({ feature, buzzLevel }) {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);
    const isHighBuzz = buzzLevel === "highbuzz";
    const title = isHighBuzz ? "バズ動画" : "非バズ動画";

    useEffect(() => {
        if (!feature) {
        return undefined;
        }

        let ignore = false;

        async function draw() {
        const encodedFeature = encodeURIComponent(feature);
        const points = await fetchJson(`/api/scatter/${buzzLevel}/${encodedFeature}`);

        if (ignore || !canvasRef.current) {
            return;
        }

        destroyChart(chartRef);

        chartRef.current = new Chart(canvasRef.current, {
            type: "scatter",
            data: {
            datasets: [
                {
                label: `${feature} と再生数の関係(${title})`,
                data: points,
                },
                {
                type: "line",
                label: `回帰直線(${title})`,
                data: regressionLine(points),
                },
            ],
            },
            options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                title: {
                    display: true,
                    text: "log(view_count)",
                },
                },
                y: {
                title: {
                    display: true,
                    text: feature,
                },
                },
            },
            },
        });
        }

        draw().catch(console.error);

        return () => {
        ignore = true;
        destroyChart(chartRef);
        };
    }, [feature, buzzLevel, title]);

    return (
        <ChartBox>
        <canvas ref={canvasRef} />
        </ChartBox>
    );
}

function ScatterSection({ featureOptions }) {
    const [selectedFeature, setSelectedFeature] = useState("");

    useEffect(() => {
        if (!selectedFeature && featureOptions.length > 0) {
        setSelectedFeature(featureOptions[0]);
        }
    }, [featureOptions, selectedFeature]);

    return (
        <Section title="散布図(特徴量ごと)">
        <select
            value={selectedFeature}
            onChange={(event) => setSelectedFeature(event.target.value)}
            style={{ minWidth: "320px", marginBottom: "16px" }}
        >
            {featureOptions.map((feature) => (
            <option key={feature} value={feature}>
                {feature}
            </option>
            ))}
        </select>

        <h3>再生数と特徴量の相関(バズ動画)</h3>
        <ScatterChart feature={selectedFeature} buzzLevel="highbuzz" />

        <h3>再生数と特徴量の相関(非バズ動画)</h3>
        <ScatterChart feature={selectedFeature} buzzLevel="lowbuzz" />
        </Section>
    );
}

function TimelineChart({ buzzLevel }) {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);
    const isBuzz = buzzLevel === "buzz";
    const title = isBuzz ? "バズ動画" : "非バズ動画";

    useEffect(() => {
        let ignore = false;

        async function draw() {
        const timelineData = await fetchJson(`/api/timeline/${buzzLevel}/`);

        if (ignore || !canvasRef.current) {
            return;
        }

        destroyChart(chartRef);

        chartRef.current = new Chart(canvasRef.current, {
            type: "line",
            data: {
            labels: timelineData.map((item) => item.section),
            datasets: [
                {
                label: `動画の盛り上がり度(${title})`,
                data: timelineData.map((item) => item.wordCountRate),
                tension: 0.5,
                fill: true,
                },
            ],
            },
            options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                title: {
                    display: true,
                    text: "動画時間",
                },
                },
                y: {
                title: {
                    display: true,
                    text: "盛り上がり度",
                },
                },
            },
            },
        });
        }

        draw().catch(console.error);

        return () => {
        ignore = true;
        destroyChart(chartRef);
        };
    }, [buzzLevel, title]);

    return (
        <ChartBox>
        <canvas ref={canvasRef} />
        </ChartBox>
    );
}

function WordCloudChart({ endpoint, label, maxSize }) {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        let ignore = false;

        async function draw() {
        const words = await fetchJson(endpoint);

        if (ignore || !canvasRef.current) {
            return;
        }

        destroyChart(chartRef);

        chartRef.current = new Chart(canvasRef.current, {
            type: "wordCloud",
            data: {
            labels: words.map((item) => item.word),
            datasets: [
                {
                label,
                data: createWordCloudSizes(words, 12, maxSize),
                },
            ],
            },
            options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: {
                word: {
                padding: 2,
                color(context) {
                    return WORD_CLOUD_COLORS[context.index % WORD_CLOUD_COLORS.length];
                },
                },
            },
            },
        });
        }

        draw().catch(console.error);

        return () => {
        ignore = true;
        destroyChart(chartRef);
        };
    }, [endpoint, label, maxSize]);

    return (
        <ChartBox tall>
        <canvas ref={canvasRef} />
        </ChartBox>
    );
}

function StrongWordsScatter() {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        let ignore = false;

        async function draw() {
        const result = await fetchJson("/api/strong_words_scatter/");
        const rawData = result.data;
        const transcriptThreshold = result.thresholds.transcript;
        const commentsThreshold = result.thresholds.comments;
        const groupedData = {};

        rawData.forEach((item) => {
            if (!groupedData[item.buzz_type]) {
            groupedData[item.buzz_type] = [];
            }

            groupedData[item.buzz_type].push(item);
        });

        if (ignore || !canvasRef.current) {
            return;
        }

        destroyChart(chartRef);

        chartRef.current = new Chart(canvasRef.current, {
            type: "scatter",
            data: {
            datasets: Object.keys(groupedData).map((type) => ({
                label: type,
                data: groupedData[type],
                backgroundColor: BUZZ_TYPE_COLORS[type] || "rgba(150, 150, 150, 0.6)",
                pointRadius: 6,
                pointHoverRadius: 9,
            })),
            },
            options: {
            responsive: true,
            maintainAspectRatio: false,
            parsing: {
                xAxisKey: "x",
                yAxisKey: "y",
            },
            scales: {
                x: {
                type: "linear",
                title: {
                    display: true,
                    text: "Transcript strong_words_score",
                    font: {
                    size: 18,
                    weight: "bold",
                    },
                },
                },
                y: {
                type: "linear",
                title: {
                    display: true,
                    text: "Comments strong_words_score",
                    font: {
                    size: 18,
                    weight: "bold",
                    },
                },
                },
            },
            plugins: {
                tooltip: {
                callbacks: {
                    label(context) {
                    const item = context.raw;

                    return [
                        `Transcript強さ: ${item.x}`,
                        `Comments強さ: ${item.y}`,
                    ];
                    },
                },
                },
                annotation: {
                annotations: {
                    transcriptLine: {
                    type: "line",
                    xMin: transcriptThreshold,
                    xMax: transcriptThreshold,
                    borderWidth: 2,
                    borderDash: [6, 6],
                    label: {
                        display: true,
                        content: "Transcriptしきい値",
                        position: "start",
                    },
                    },
                    commentsLine: {
                    type: "line",
                    yMin: commentsThreshold,
                    yMax: commentsThreshold,
                    borderWidth: 2,
                    borderDash: [6, 6],
                    label: {
                        display: true,
                        content: "Commentsしきい値",
                        position: "start",
                    },
                    },
                },
                },
            },
            },
        });
        }

        draw().catch(console.error);

        return () => {
        ignore = true;
        destroyChart(chartRef);
        };
    }, []);

    return (
        <ChartBox>
        <canvas ref={canvasRef} />
        </ChartBox>
    );
}

function MedianRatioChart({ video }) {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    const comparisons = useMemo(
        () => video.comparisons.filter((item) => item.ratio !== null),
        [video.comparisons]
    );

    useEffect(() => {
        if (!canvasRef.current) {
        return undefined;
        }

        const ratios = comparisons.map((item) => Number(item.ratio.toFixed(2)));

        destroyChart(chartRef);

        chartRef.current = new Chart(canvasRef.current, {
        type: "bar",
        data: {
            labels: comparisons.map((item) => item.feature),
            datasets: [
            {
                label: "中央値比",
                data: ratios,
                backgroundColor: ratios.map((value) =>
                value >= 1 ? "rgba(54, 162, 235, 0.75)" : "rgba(255, 159, 64, 0.75)"
                ),
            },
            ],
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            scales: {
            x: {
                beginAtZero: true,
                title: {
                display: true,
                text: "中央値比",
                },
            },
            },
            plugins: {
            tooltip: {
                callbacks: {
                label(context) {
                    const item = comparisons[context.dataIndex];

                    return [
                    `中央値比: ${context.raw}`,
                    `値: ${item.value}`,
                    `中央値: ${item.median}`,
                    ];
                },
                },
            },
            },
        },
        });

        return () => destroyChart(chartRef);
    }, [comparisons]);

    return (
        <ChartBox>
        <canvas ref={canvasRef} />
        </ChartBox>
    );
}

function VideoComparison() {
    const [videos, setVideos] = useState([]);
    const [selectedIds, setSelectedIds] = useState([]);
    const [status, setStatus] = useState("");
    const [comparisonVideos, setComparisonVideos] = useState([]);

    useEffect(() => {
        let ignore = false;

        async function loadOptions() {
        const options = await fetchJson("/api/analyze_videos/");

        if (!ignore) {
            setVideos(options);
        }
        }

        loadOptions().catch(console.error);

        return () => {
        ignore = true;
        };
    }, []);

    async function compareSelectedVideos() {
        if (selectedIds.length === 0) {
        setComparisonVideos([]);
        setStatus("比較する動画を選択してください。");
        return;
        }

        const params = new URLSearchParams();
        selectedIds.forEach((videoId) => params.append("video_id", videoId));
        params.append("top_n", "15");

        setStatus("比較データを取得中...");
        const result = await fetchJson(`/api/analyze_result/?${params.toString()}`);

        setComparisonVideos(result.videos);
        setStatus("");
    }

    return (
        <Section title="動画比較">
        <div
            style={{
            display: "flex",
            gap: "12px",
            alignItems: "flex-end",
            flexWrap: "wrap",
            }}
        >
            <label>
            動画タイトル
            <select
                multiple
                value={selectedIds}
                onChange={(event) => {
                const ids = Array.from(event.target.selectedOptions).map(
                    (option) => option.value
                );
                setSelectedIds(ids);
                }}
                style={{
                display: "block",
                minWidth: "320px",
                minHeight: "140px",
                marginTop: "8px",
                }}
            >
                {videos.map((video) => (
                <option key={video.video_id} value={video.video_id}>
                    {video.title}
                </option>
                ))}
            </select>
            </label>

            <button
            type="button"
            onClick={() => {
                compareSelectedVideos().catch(console.error);
            }}
            style={{
                padding: "8px 16px",
                cursor: "pointer",
            }}
            >
            選択した動画を比較
            </button>
        </div>

        {status && <p>{status}</p>}

        {comparisonVideos.map((video) => (
            <section
            key={video.video_id}
            style={{
                marginTop: "20px",
                paddingTop: "16px",
                borderTop: "1px solid #ddd",
            }}
            >
            <h3>{video.title}</h3>
            <p>
                再生数:{" "}
                {video.view_count === null
                ? "不明"
                : Math.round(video.view_count).toLocaleString()}
            </p>
            <p>buzz_type: {video.buzz_type}</p>
            <MedianRatioChart video={video} />
            </section>
        ))}
        </Section>
    );
}

function ResultChartApp() {
    const [featureOptions, setFeatureOptions] = useState(
        window.RESULT_CHART_FEATURES || []
    );

    const handleFeaturesLoaded = useCallback((featuresFromShap) => {
        setFeatureOptions((current) => {
        if (current.length > 0) {
            return current;
        }

        return featuresFromShap;
        });
    }, []);

    return (
        <main
        style={{
            fontFamily: "system-ui, sans-serif",
            padding: "24px",
            lineHeight: 1.6,
        }}
        >
        <h1>分析結果</h1>

        <Section title="SHAPグラフ">
            <p>どの特徴量がバズに関係しているかを表示します。</p>
            <ShapChart onFeaturesLoaded={handleFeaturesLoaded} />
        </Section>

        <ScatterSection featureOptions={featureOptions} />

        <Section title="動画の各セクションごとの盛り上がり度(バズ動画)">
            <TimelineChart buzzLevel="buzz" />
        </Section>

        <Section title="動画の各セクションごとの盛り上がり度(非バズ動画)">
            <TimelineChart buzzLevel="nonbuzz" />
        </Section>

        <Section title="コメントの頻出ワードのワードクラウド">
            <WordCloudChart
            endpoint="/api/wordcloud/comment/"
            label="ワードクラウド(コメント頻出語)"
            maxSize={40}
            />
        </Section>

        <Section title="動画タグの頻出ワードのワードクラウド">
            <WordCloudChart
            endpoint="/api/wordcloud/tag/"
            label="ワードクラウド(タグ頻出語)"
            maxSize={44}
            />
        </Section>

        <Section title="動画タイトルの頻出ワードのワードクラウド">
            <WordCloudChart
            endpoint="/api/wordcloud/word/"
            label="ワードクラウド(タイトル頻出語)"
            maxSize={44}
            />
        </Section>

        <Section title="strong_words のスコアによるバズ傾向の分類">
            <ul>
            <li>transcript と comment の両方が強い: 本物バズ</li>
            <li>transcript だけが強い: 釣り・内容先行型</li>
            <li>comment だけが強い: 共感型</li>
            <li>どちらも低い: 低反応型</li>
            </ul>
            <StrongWordsScatter />
        </Section>

        <VideoComparison />
        </main>
    );
}

const rootElement = document.getElementById("react-result-chart-root");

if (rootElement) {
    ReactDOM.createRoot(rootElement).render(<ResultChartApp />);
}
