// グラフを保持する変数
let timelineChartbuzz;
let timelineChartnonbuzz;

// グラフを作る関数
export async function createtimelineChart() {
    // Flask APIへアクセス
    const response_timeline_buzz = await fetch("/api/timeline/buzz/");
    // JSONへ変換
    const timeline_data_buzz = await response_timeline_buzz.json();
    const response_timeline_non_buzz = await fetch("/api/timeline/nonbuzz/");
    const timeline_data_non_buzz = await response_timeline_non_buzz.json();
    const labels_buzz = timeline_data_buzz.map(item => item.section)
    const wordcount_buzz = timeline_data_buzz.map(item => item.wordCountRate)
    const labels_non_buzz = timeline_data_non_buzz.map(item => item.section)
    const wordcount_non_buzz = timeline_data_non_buzz.map(item => item.wordCountRate)
    // canvas取得
    const ctx_four = document.getElementById("timelineChartbuzz");
    const ctx_five = document.getElementById("timelineChartnonbuzz");
    // 既存グラフがあるなら削除
    // Chart.js生成
    timelineChartbuzz = new Chart(ctx_four, {

        type: "line",
        data: {
            labels: labels_buzz,
            datasets: [
                {
                    label: "動画の盛り上がり(バズ動画)",
                    data: wordcount_buzz,
                    tension: 0.5,
                    fill: true,
        }
    ]},
        options: {
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "動画時間"
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: "盛り上がり"
                    }
                }
            }
        }
    });
// Chart.js生成
    timelineChartnonbuzz = new Chart(ctx_five, {

        type: "line",
        data: {
            labels: labels_non_buzz,
            datasets: [
        {
                    label: "動画の盛り上がり(非バズ動画)",
                    data: wordcount_non_buzz,
                    tension: 0.5,
                    fill: true,
        }
    ]},
        options: {
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "動画時間"
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: "盛り上がり"
                    }
                }
            }
        }
    });
}            
