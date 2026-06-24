import { createSHAPChart } from "./SHAP_chart.js";
import { createtimelineChart } from "./timeline_chart.js";
import { createwordcloudChart } from "./word_cloud.js";
import { createStrongWordsScatter } from "./strong_word_scatter.js";
import { loadCompareVideoOptions, setupCompareVideoEvents } from "./result_display.js";
import { MODELDETAILSDISPLAY } from "./model_details.js";

// 全てのhtmlが読み込まれたらinitResultCharts()が発火する
document.addEventListener("DOMContentLoaded", () => {
  initResultCharts();
});

// 複数のPromiseがすべて完了するまで待つ
function initResultCharts() {
  Promise.allSettled([
    createSHAPChart(),
    createtimelineChart(),
    createwordcloudChart(),
    createStrongWordsScatter(),
    loadCompareVideoOptions(),
    MODELDETAILSDISPLAY(),
  // 全てのPromiseの処理が完了したらresults以降の処理が行われる
  ]).then(results => {
    results
      .filter(result => result.status === "rejected")
      .forEach(result => console.error(result.reason));
  });

  setupCompareVideoEvents();
}
