# バックグラウンドジョブ方式の処理フロー

このドキュメントは、`route.py` に追加したバックグラウンドジョブ方式で、画面表示と重い処理、データ受け渡しがどう動いているかを整理したものです。

## 目的

以前の同期処理では、フォーム送信後に `main_process.collect()` や `main_process.analyze()` が終わるまで Flask がレスポンスを返せませんでした。

そのため、処理中画面を表示したい場合は、次のように役割を分けます。

```text
画面表示用のリクエスト
重い処理を実行するバックグラウンドジョブ
処理状況を確認するAPI
完了後に移動する結果画面
```

## 全体フロー

```text
1. input.html のフォームから POST /run に送信する

2. route.py の run() が呼ばれる
   - run_mode を受け取る
   - job_id を作る
   - JOBS にジョブ状態を保存する
   - 別スレッドで run_background_job(job_id, run_mode) を開始する
   - processing.html をすぐブラウザへ返す

3. processing.html が表示される
   - HTML内に job_id が埋め込まれている
   - JavaScript が /api/job_status/<job_id> を定期的に fetch する

4. バックグラウンド側で main_process.* が実行される
   - analyze なら分析結果データをグローバル変数に保存する
   - collect / NLP_analyze なら処理だけ実行する
   - 完了したら JOBS[job_id] を done に更新する

5. processing.html 側が done を検知する
   - job.result_url に自動遷移する
   - analyze は /result
   - collect / NLP_analyze は /complete
```

## route.py 側の役割

### ジョブ状態の保存場所

`route.py` では、簡易的にメモリ上の辞書でジョブ状態を管理しています。

```python
JOBS = {}
JOBS_LOCK = threading.Lock()
```

`JOBS` には、ジョブIDごとに次のようなデータが入ります。

```python
{
    "status": "running",
    "mode": run_mode,
    "result_url": None,
    "error": None
}
```

処理が終わると、例えば次のようになります。

```python
{
    "status": "done",
    "mode": "analyze",
    "result_url": "/result",
    "error": None
}
```

エラー時は次のようになります。

```python
{
    "status": "error",
    "mode": "analyze",
    "result_url": None,
    "error": "エラーメッセージ"
}
```

`JOBS_LOCK` は、画面側の状態確認APIとバックグラウンドスレッドが同時に `JOBS` を触るため、競合を避ける目的で使います。

## POST /run の役割

`/run` は、フォームから送信された `mode` を受け取り、ジョブを開始します。

```python
@app.route("/run", methods=["POST"])
def run():
    run_mode = request.form.get("mode")
    job_id = uuid.uuid4().hex

    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "running",
            "mode": run_mode,
            "result_url": None,
            "error": None
        }

    thread = threading.Thread(
        target=run_background_job,
        args=(job_id, run_mode),
        daemon=True
    )
    thread.start()

    return render_template("processing.html", job_id=job_id)
```

重要なのは、ここでは重い処理の完了を待たないことです。

`thread.start()` で別スレッドに処理を任せたあと、すぐに `processing.html` を返します。

## run_background_job() の役割

`run_background_job()` が実際の重い処理を担当します。

```python
def run_background_job(job_id, run_mode):
    global shap_importance_df_output, scatter_df, buzz_videos_df, non_buzz_videos_df, trend_comment_df, trend_tag_df, trend_word_df, output_df, strong_words_scatter_df

    try:
        if run_mode == "analyze":
            shap_importance_df_output, scatter_df, buzz_videos_df, non_buzz_videos_df, trend_comment_df, trend_tag_df, trend_word_df, output_df, strong_words_scatter_df = main_process.analyze()
            update_job(job_id, status="done", result_url="/result")
        elif run_mode == "collect":
            main_process.collect()
            update_job(job_id, status="done", result_url="/complete")
        elif run_mode == "NLP_analyze":
            main_process.NLP_processing()
            update_job(job_id, status="done", result_url="/complete")
        else:
            update_job(job_id, status="error", error="Invalid run mode.")
    except Exception as exc:
        update_job(job_id, status="error", error=str(exc))
```

### analyze のデータ受け渡し

`analyze` の場合、`main_process.analyze()` は複数のDataFrameを返します。

それらは `route.py` のグローバル変数に保存されます。

```python
shap_importance_df_output
scatter_df
buzz_videos_df
non_buzz_videos_df
trend_comment_df
trend_tag_df
trend_word_df
output_df
strong_words_scatter_df
```

このデータは、後続の `/result` や各APIで参照されます。

例:

```python
@app.route("/result", methods=["GET"])
def result_display():
    feature_labels = [
        column for column in scatter_df.columns
        if column not in ["view_count", "video_id", "title"]
    ]
    return render_template("result_chart.html", feature_labels=feature_labels)
```

`result_chart.html` が表示されたあと、各グラフ用JavaScriptが次のAPIを呼び、グローバル変数からJSON化されたデータを受け取ります。

```text
/api/shap
/api/scatter/highbuzz/<feature>
/api/scatter/lowbuzz/<feature>
/api/timeline/buzz/
/api/timeline/nonbuzz/
/api/wordcloud/comment/
/api/wordcloud/tag/
/api/wordcloud/word/
/api/strong_words_scatter/
/api/analyze_videos/
/api/analyze_result/
```

つまり、`analyze` のデータ受け渡しは次の形です。

```text
main_process.analyze()
→ route.py のグローバル変数
→ /result
→ result_chart.html
→ 各JSがAPIをfetch
→ APIがグローバル変数をJSONにして返す
→ Chart.jsで描画
```

### collect / NLP_analyze のデータ受け渡し

`collect` と `NLP_analyze` は、現状ではグラフ表示用のDataFrameを画面に渡していません。

処理完了後は `/complete` に移動し、`result.html` を表示します。

```text
main_process.collect()
→ JOBS[job_id] を done に更新
→ result_url = /complete
→ processing.html が /complete に遷移
→ result.html を表示
```

`NLP_analyze` も同じです。

## /api/job_status/<job_id> の役割

`processing.html` から呼ばれる状態確認APIです。

```python
@app.route("/api/job_status/<job_id>", methods=["GET"])
def job_status(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)

    if job is None:
        return jsonify({"status": "error", "error": "Job not found."}), 404

    return jsonify(job)
```

返却例:

```json
{
  "status": "running",
  "mode": "analyze",
  "result_url": null,
  "error": null
}
```

完了時:

```json
{
  "status": "done",
  "mode": "analyze",
  "result_url": "/result",
  "error": null
}
```

## processing.html 側の役割

`processing.html` は、`/run` から渡された `job_id` を使ってジョブ状態を確認します。

```javascript
const jobId = "{{ job_id }}";
```

その後、`pollJobStatus()` が定期的にAPIを呼びます。

```javascript
const response = await fetch(`/api/job_status/${jobId}`);
const job = await response.json();
```

状態ごとの動きは次の通りです。

```text
job.status === "running"
→ 2秒後にもう一度確認

job.status === "done"
→ job.result_url に移動

job.status === "error"
→ 画面にエラーメッセージを表示して停止
```

完了時の遷移:

```javascript
window.location.href = job.result_url;
```

## 画面遷移まとめ

### analyze

```text
input.html
→ POST /run
→ processing.html
→ /api/job_status/<job_id> をポーリング
→ main_process.analyze() 完了
→ /result
→ result_chart.html
→ 各グラフJSがAPIからデータ取得
→ グラフ表示
```

### collect

```text
input.html
→ POST /run
→ processing.html
→ /api/job_status/<job_id> をポーリング
→ main_process.collect() 完了
→ /complete
→ result.html
```

### NLP_analyze

```text
input.html
→ POST /run
→ processing.html
→ /api/job_status/<job_id> をポーリング
→ main_process.NLP_processing() 完了
→ /complete
→ result.html
```

## 現在残っている旧ルート

現在の `route.py` には、旧方式の名残として次のルートがあります。

```python
@app.route("/process_legacy/<run_mode>", methods=["GET"])
def run_process(run_mode):
    return redirect(url_for("booting"))
```

現状のバックグラウンドジョブ方式では使用していません。

今後、参照する予定がなければ削除して問題ありません。

## 注意点

この実装は、開発環境向けの簡易バックグラウンドジョブ方式です。

`JOBS` と分析結果DataFrameは、Flaskプロセス内のメモリに保存されています。そのため、次の制約があります。

- Flaskプロセスを再起動するとジョブ状態と分析結果は消える
- 複数プロセス構成では、別プロセスから `JOBS` やグローバル変数が見えない
- 複数ユーザーが同時に `analyze` を実行すると、グローバル変数が後から実行した結果で上書きされる
- 長時間ジョブや本番運用では、Celery、RQ、データベース保存などに移す方が安全

個人開発やローカル実行で「処理中画面を表示しながら重い処理を待つ」目的なら、この構成で十分です。
