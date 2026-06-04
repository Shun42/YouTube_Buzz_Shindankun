import { createSHAPChart } from "./SHAP_chart.js";
import { createtimelineChart } from "./timeline_chart.js";
import { setupScatterChartEvents } from "./scatter_chart.js";
import { createwordcloudChart } from "./word_cloud.js";
import { createStrongWordsScatter } from "./strong_word_scatter.js";
import { loadCompareVideoOptions, setupCompareVideoEvents } from "./result_display.js";

document.addEventListener("DOMContentLoaded", () => {
    initResultCharts();
});

function initResultCharts() {
    createSHAPChart();
    setupScatterChartEvents();
    createtimelineChart();
    createwordcloudChart();
    createStrongWordsScatter();
    loadCompareVideoOptions();
    setupCompareVideoEvents();
}
