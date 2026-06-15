import { fetchJson } from "./fetch_json.js";

 // グラフを保持する変数
let scatterChartHighbuzz;
let scatterChartLowbuzz;
        // グラフを作る関数
async function createscatterChart(feature) {
            const encodedFeature = encodeURIComponent(feature);
            // Flask APIへアクセス
            const scatter_data_high_buzz = await fetchJson(`/api/scatter/highbuzz/${encodedFeature}`);
            const scatter_data_low_buzz = await fetchJson(`/api/scatter/lowbuzz/${encodedFeature}`);

            // canvas取得
            const ctx_two = document.getElementById("scatterChartHigh");
            const ctx_three = document.getElementById("scatterChartLow");
            // 既存グラフがあるなら削除
            if (scatterChartHighbuzz) {
                scatterChartHighbuzz.destroy();
                scatterChartLowbuzz.destroy();
            }

            const linest = (obj) => {

            const n = obj.length;

            const X = obj.reduce((sum, v) => sum + v.x, 0);

            const Y = obj.reduce((sum, v) => sum + v.y, 0);

            const XX = obj.reduce((sum, v) => sum + v.x * v.x, 0);

            const XY = obj.reduce((sum, v) => sum + v.x * v.y, 0);

            // 傾き
            const a = (n * XY - X * Y) / (n * XX - X * X);

            // 切片
            const b = (XX * Y - XY * X) / (n * XX - X * X);

            return { a, b };

            }

            const { a: buzz_a, b: buzz_b } = linest(scatter_data_high_buzz)
            const { a: low_buzz_a, b: low_buzz_b } = linest(scatter_data_low_buzz)

            // 回帰直線用
            const buzz_arr = [];
            const low_buzz_arr = [];
            scatter_data_high_buzz.forEach(function (v) {
            buzz_arr.push({ 'x': v.x, 'y': buzz_a * v.x + buzz_b });
            });
            scatter_data_low_buzz.forEach(function (v) {
            low_buzz_arr.push({ 'x': v.x, 'y': low_buzz_a * v.x + low_buzz_b });
            });
            buzz_arr.sort((p1, p2) => p1.x - p2.x);
            low_buzz_arr.sort((p1, p2) => p1.x - p2.x);

            // Chart.js生成
            scatterChartHighbuzz = new Chart(ctx_two, {

                type: "scatter",
                data: {
                    datasets: [
                        {
                            label: `${feature} と再生数の関係(高バズ)`,
                            data: scatter_data_high_buzz
                },
                {
                    type: 'line',
                    label: '回帰直線(高バズ)',
                    data: buzz_arr
                }
            ]},
                options: {
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: "再生数(対数)"
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: feature
                            }
                        }
                    }
                }
            });
            scatterChartLowbuzz = new Chart(ctx_three, {

                type: "scatter",
                data: {
                    datasets: [
                {
                            label: `${feature} と再生数の関係(低バズ)`,
                            data: scatter_data_low_buzz
                },
                {
                    type: 'line',
                    label: '回帰直線(低バズ)',
                    data: low_buzz_arr
                }
            ]},
                options: {
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: "再生数(対数)"
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: feature
                            }
                        }
                    }
                }
            });
        }            
export function setupScatterChartEvents() {
            const featureSelect = document.getElementById("featureSelect");

            if (!featureSelect) {
                return;
            }

            featureSelect.addEventListener("change", function () {
                createscatterChart(this.value).catch(error => console.error(error));
            });

            createscatterChart(featureSelect.value).catch(error => console.error(error));
        }
