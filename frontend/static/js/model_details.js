import { fetchJson } from "./fetch_json.js";

export async function MODELDETAILSDISPLAY() {
  const modelDetails = await fetchJson("/api/model_details");
  const bestModelInfo = modelDetails.best_model;

  const bestModelContainer = document.getElementById("best_model");
  const bestModelIndexContainer = document.getElementById("best_model_index");
  const modelsDetailContainer = document.getElementById("models_detail");
  if (!bestModelContainer || !bestModelIndexContainer || !modelsDetailContainer) {
    return;
  }

// modelDetails.modelsの内容をまずhtml列にしてからそれらを空白無しでjoinする
  const modelsHtml = modelDetails.models.map((modelInfo) => {
    return `
      <tr>
        <td>${modelInfo.model_name}</td>
        <td>${modelInfo.rmsle}</td>
        <td>${modelInfo.mae}</td>
        <td>${modelInfo.r2}</td>
      </tr>
    `;
  }).join("");

  // bestModelContainer内にHTMLを入れる
  bestModelContainer.innerHTML = `<p>最も正確だったモデルは${bestModelInfo.model_name}です。</p>`;
  bestModelIndexContainer.innerHTML = `
    <ul>
      <li>RMSLE: ${bestModelInfo.rmsle}</li>
      <li>MAE: ${bestModelInfo.mae}</li>
      <li>R2: ${bestModelInfo.r2}</li>
    </ul>
  `;
  modelsDetailContainer.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>モデル名</th>
          <th>RMSLE</th>
          <th>MAE</th>
          <th>R2</th>
        </tr>
      </thead>
      <tbody>
        ${modelsHtml}
      </tbody>
    </table>
  `;
}
