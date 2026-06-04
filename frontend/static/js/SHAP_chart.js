// グラフを保持する変数
let SHAP_chart;

// グラフを作る関数
export async function createSHAPChart() {
    // Flask APIへアクセス
    const response = await fetch("/api/shap");
    // JSONへ変換
    const shap_data = await response.json();
    const labels = shap_data.map(item => item.feature);
    const importances = shap_data.map(item => item.importance);
    console.log(shap_data);
    // canvas取得
    const ctx = document.getElementById("SHAPChart");
    // 既存グラフがあるなら削除
    if (SHAP_chart) {
        SHAP_chart.destroy();
    }
    // Chart.js生成
    SHAP_chart = new Chart(ctx, {

        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "SHAP値",
                data: importances,
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
