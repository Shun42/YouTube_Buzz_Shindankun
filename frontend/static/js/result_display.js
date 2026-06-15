import { fetchJson } from "./fetch_json.js";

let comparisonCharts = [];
// 'output_df' から 'video_id' と 'title' を取り出して、JSONで返す
// 返ってきたデータから"compareVideoSelect"を生成する
export async function loadCompareVideoOptions() {
    const videos = await fetchJson("/api/analyze_videos/");
    const select = document.getElementById("compareVideoSelect");
    select.innerHTML = "";

    videos.forEach(video => {
        const option = document.createElement("option");
        option.value = video.video_id;
        option.textContent = video.title;
        select.appendChild(option);
    });
}

function destroyComparisonCharts() {
    comparisonCharts.forEach(chart => chart.destroy());
    comparisonCharts = [];
}
// comparisonsのdeviationをChart.jsに渡す
function createDeviationChart(canvas, video) {
    const comparisons = video.comparisons.filter(item => item.deviation !== null);
    const labels = comparisons.map(item => item.feature);
    const deviations = comparisons.map(item => Number(item.deviation.toFixed(1)));
    const minDeviation = Math.min(...deviations);
    const maxDeviation = Math.max(...deviations);
    const axisMin = Math.floor(Math.min(0, minDeviation) / 10) * 10;
    const axisMax = Math.ceil(Math.max(100, maxDeviation) / 10) * 10;
    const colors = deviations.map(value =>
        value >= 50 ? "rgba(54, 162, 235, 0.75)" : "rgba(255, 159, 64, 0.75)"
    );
    // 横棒グラフを作る
    return new Chart(canvas, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "偏差値",
                data: deviations,
                backgroundColor: colors
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    min: axisMin,
                    suggestedMax: axisMax,
                    title: {
                        display: true,
                        text: "偏差値"
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const item = comparisons[context.dataIndex];
                            return [
                                `偏差値: ${context.raw}`,
                                `値: ${item.value}`,
                                `平均: ${item.mean}`,
                                `標準偏差: ${item.std}`
                            ];
                        }
                    }
                }
            }
        }
    });
}
// 選択された動画IDを集め、URLパラメータにしてAPIへ送る
async function compareSelectedVideos() {
    const status = document.getElementById("comparisonStatus");
    const results = document.getElementById("comparisonResults");
    const select = document.getElementById("compareVideoSelect");
    const selectedIds = Array.from(select.selectedOptions).map(option => option.value);

    destroyComparisonCharts();
    results.innerHTML = "";

    if (selectedIds.length === 0) {
        status.textContent = "比較する動画を選択してください。";
        return;
    }

    const params = new URLSearchParams();
    selectedIds.forEach(videoId => params.append("video_id", videoId));
    params.append("top_n", "15");
    
    // URLパラメータにしてAPIへ送る
    status.textContent = "比較データを取得中...";
    const result = await fetchJson(`/api/analyze_result/?${params.toString()}`);

    // 返ってきたvideosを1件ずつ処理
    result.videos.forEach((video, index) => {
        // 動画ごとにカードを作る
        const card = document.createElement("section");
        card.className = "comparison-card";

        const title = document.createElement("h3");
        title.textContent = video.title;

        const viewCount = document.createElement("p");
        viewCount.className = "comparison-meta";
        const formattedViewCount = video.view_count === null
            ? "不明"
            : Math.round(video.view_count).toLocaleString();
        viewCount.textContent = `再生数: ${formattedViewCount}`;

        const buzzType = document.createElement("p");
        buzzType.className = "comparison-meta";
        buzzType.textContent = `buzz_type: ${video.buzz_type}`;

        const canvas = document.createElement("canvas");
        canvas.id = `comparisonChart${index}`;

        card.appendChild(title);
        card.appendChild(viewCount);
        card.appendChild(buzzType);
        card.appendChild(canvas);
        results.appendChild(card);

        comparisonCharts.push(createDeviationChart(canvas, video));
    });
}

export function setupCompareVideoEvents() {
    const compareButton = document.getElementById("compareVideosButton");

    if (compareButton) {
        compareButton.addEventListener("click", () => {
            compareSelectedVideos().catch(error => {
                console.error(error);
                const status = document.getElementById("comparisonStatus");
                if (status) {
                    status.textContent = "比較データの取得に失敗しました。";
                }
            });
        });
    }
}
