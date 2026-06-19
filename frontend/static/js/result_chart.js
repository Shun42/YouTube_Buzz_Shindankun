import { createSHAPChart } from "./SHAP_chart.js";
import { createtimelineChart } from "./timeline_chart.js";
import { createwordcloudChart } from "./word_cloud.js";
import { createStrongWordsScatter } from "./strong_word_scatter.js";
import { loadCompareVideoOptions, setupCompareVideoEvents } from "./result_display.js";
import { MODELDETAILSDISPLAY } from "./model_details.js";

document.addEventListener("DOMContentLoaded", () => {
  initResultCharts();
});

function initResultCharts() {
  Promise.allSettled([
    createSHAPChart(),
    createtimelineChart(),
    createwordcloudChart(),
    createStrongWordsScatter(),
    loadCompareVideoOptions(),
    MODELDETAILSDISPLAY(),
  ]).then(results => {
    results
      .filter(result => result.status === "rejected")
      .forEach(result => console.error(result.reason));
  });

  setupCompareVideoEvents();
}
