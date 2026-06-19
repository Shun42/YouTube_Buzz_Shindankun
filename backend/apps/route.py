from flask import redirect, url_for, render_template, request, jsonify, Response
import threading
import uuid
import main_process
import pandas as pd
import numpy as np
from analysis.data_regression import FEATURE_LABELS


REVERSE_FEATURE_LABELS = {label: feature for feature, label in FEATURE_LABELS.items()}
JOBS = {}
JOBS_LOCK = threading.Lock()

# 外れ値除去
def outliner_remove(df, feature):
    if feature not in scatter_df.select_dtypes(include="number").columns:
        return jsonify({"error": "numeric feature not found"}), 400
    q1 = df[feature].quantile(0.25)
    q3 = df[feature].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return df[(df[feature] >= lower) & (df[feature] <= upper)].copy()

def to_json_number(value):
    if pd.isna(value):
        return None
    value = float(value)
    if not np.isfinite(value):
        return None
    return value

# JOBS辞書の更新
def update_job(job_id, **values):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(values)

# run関数で生成されたjob_id, run_modeを引数にして実処理を行う
def run_background_job(job_id, run_mode):
    global shap_importance_df_output, scatter_df, buzz_videos_df, non_buzz_videos_df, trend_comment_df, trend_tag_df, trend_word_df, output_df, strong_words_scatter_df, models_output, best_result_model

    try:
        if run_mode == "analyze":
            shap_importance_df_output, scatter_df, buzz_videos_df, non_buzz_videos_df, trend_comment_df, trend_tag_df, trend_word_df, output_df, strong_words_scatter_df, models_output, best_result_model = main_process.analyze()
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

# バズの型の分類
# commentとtranscriptの、strong_wordの量(thresholdより多いかどうか)で分類
def classify(row, transcript_threshold, comments_threshold):
    transcript_strong = row["strong_transcript_score"] >= transcript_threshold
    comments_strong = row["strong_comment_score"] >= comments_threshold

    if transcript_strong and comments_strong:
        return "本物バズ"
    elif transcript_strong and not comments_strong:
        return "釣り・内容先行型"
    elif not transcript_strong and comments_strong:
        return "共感型"
    else:
        return "低反応型"
    
# 起動画面
def register_routes(app):
    @app.route("/favicon.ico")
    def favicon():
        return Response(status=204)

    @app.route("/", methods=["GET"])
    def booting():
        return render_template("input.html")
    
    # 起動モードが選択されると呼ばれる
    # 選ばれた起動モードによって分岐
    @app.route("/run", methods=["POST"])
    def run():
        run_mode = request.form.get("mode")

        # job_idを作りHTML内に埋め込みprocessing.htmlに送る
        job_id = uuid.uuid4().hex

        # jobの状態
        with JOBS_LOCK:
            JOBS[job_id] = {
                "status": "running",
                "mode": run_mode,
                "result_url": None,
                "error": None
            }

        # 別スレッドで実処理を行う
        thread = threading.Thread(
            target=run_background_job,
            args=(job_id, run_mode),
            daemon=True
        )
        thread.start()

        return render_template("processing.html", job_id=job_id)
        
    # データ収集モードとNLP分析モードの結果画面
    @app.route("/api/job_status/<job_id>", methods=["GET"])
    def job_status(job_id):
        with JOBS_LOCK:
            job = JOBS.get(job_id)

        if job is None:
            return jsonify({"status": "error", "error": "Job not found."}), 404
        # processing.htmlにJOBSの状態を送る
        return jsonify(job)

    # processing.htmlから返されたURLによってcompleteとresult_displayに分岐
    @app.route("/complete", methods=["GET"])
    def complete():
        return render_template("result.html")

    @app.route("/result", methods=["GET"])
    def result_display():
        feature_labels = [
            column for column in scatter_df.columns
            if column not in ["view_count", "video_id", "title"]
        ]
        return render_template("result_chart.html", feature_labels=feature_labels)
    
    @app.route("/api/model_details", methods=["GET"])
    def model_display():
        if "models_output" not in globals() or "best_result_model" not in globals():
            return jsonify({"error": "model details are not ready"}), 404
        return jsonify({
            "best_model": best_result_model,
            "models": models_output
        })

    # SHAPグラフに渡すjsonデータの作成
    @app.route("/api/shap", methods=["GET"])
    def shap_chart():
        shap_data = []
        for _, row in shap_importance_df_output.iterrows():

            shap_data.append({
                "feature": row["feature"],
                "importance": row["importance"]
            })

        return jsonify(shap_data)

    
    # 時系列グラフに渡すバズ動画のjsonデータの作成
    @app.route("/api/timeline/buzz/", methods=["GET"])
    def timeline_chart_highbuzz():
        transcriptcount_buzz = []
        for _, row in buzz_videos_df.iterrows():
            transcriptcount_buzz.append({
            "section": row["section"],
            "wordCountRate": row["wordCountRate"]
            })
        return jsonify(transcriptcount_buzz)
    
    # 時系列グラフに渡す非バズ動画のjsonデータの作成
    @app.route("/api/timeline/nonbuzz/", methods=["GET"])
    def timeline_chart_non_buzz():
        transcriptcount_non_buzz = []
        for _, row in non_buzz_videos_df.iterrows():
            transcriptcount_non_buzz.append({
            "section": row["section"],
            "wordCountRate": row["wordCountRate"]
            })
        return jsonify(transcriptcount_non_buzz)
    
    # コメントのtrend_wordのワードクラウドに渡すjsonデータの作成
    @app.route("/api/wordcloud/comment/", methods=["GET"])
    def trend_comment():
        trend_comment_data = []
        for _, row in trend_comment_df.iterrows():
            trend_comment_data.append({
            "word": str(row["trend_comments"]),
            "count": int(row["trend_commnets_count"])
            })
        return jsonify(trend_comment_data)
    
    # タグのtrend_wordのワードクラウドに渡すjsonデータの作成
    @app.route("/api/wordcloud/tag/", methods=["GET"])
    def trend_tag():
        trend_tag_data = []
        for _, row in trend_tag_df.iterrows():
            trend_tag_data.append({
            "word": str(row["trend_tags"]),
            "count": int(row["trend_tags_count"])
            })
        return jsonify(trend_tag_data)
    
    # タイトルのtrend_wordのワードクラウドに渡すjsonデータの作成
    @app.route("/api/wordcloud/word/", methods=["GET"])
    def trend_word():
        trend_word_data = []
        for _, row in trend_word_df.iterrows():
            trend_word_data.append({
            "word": str(row["trend_words"]),
            "count": int(row["trend_words_count"])
            })
        return jsonify(trend_word_data)
    
    # コメントとtranscriptのstrong_wordの多さによる動画の分類の散布図に渡すjsonデータの作成
    @app.route("/api/strong_words_scatter/", methods=["GET"])
    def strong_words_scatter():
        data = []
        log_strong_words_scatter_df = strong_words_scatter_df[["strong_transcript_score", "strong_comment_score"]].copy()
        log_strong_words_scatter_df = log_strong_words_scatter_df.apply(np.log1p)
        transcript_threshold = log_strong_words_scatter_df["strong_transcript_score"].quantile(0.75)
        comments_threshold = log_strong_words_scatter_df["strong_comment_score"].quantile(0.75)
        log_strong_words_scatter_df["buzz_type"] = log_strong_words_scatter_df.apply(classify, args=(transcript_threshold, comments_threshold),axis=1)
        for _, row in log_strong_words_scatter_df.iterrows():
            data.append({
            "x": float(row["strong_transcript_score"]),
            "y": float(row["strong_comment_score"]),
            "buzz_type": row["buzz_type"]
            })

        strong_words_scatter_data = {"data": data,
        "thresholds": {
            "transcript": float(transcript_threshold),
            "comments": float(comments_threshold)
        }}
        return jsonify(strong_words_scatter_data)
    
    @app.route("/api/strong_words_scatter_output/", methods=["GET"])
    def strong_words_scatter_output():
        strong_words_scatter_data = []
        strong_words_scatter_output_df = strong_words_scatter_df[["video_id", "title", "strong_transcript_score", "strong_comment_score"]].copy()
        transcript_threshold = strong_words_scatter_output_df["strong_transcript_score"].quantile(0.75)
        comments_threshold = strong_words_scatter_output_df["strong_comment_score"].quantile(0.75)
        strong_words_scatter_output_df["buzz_type"] = strong_words_scatter_output_df.apply(classify, args=(transcript_threshold, comments_threshold),axis=1)
        strong_comments_transcript_video_df = strong_words_scatter_output_df[strong_words_scatter_output_df["buzz_type"] == "本物バズ"].head(1)
        strong_comments_video_df = strong_words_scatter_output_df[strong_words_scatter_output_df["buzz_type"] == "共感型"].head(1)
        strong_transcripts_video_df = strong_words_scatter_output_df[strong_words_scatter_output_df["buzz_type"] == "釣り・内容先行型"].head(1)
        non_strong_video_df = strong_words_scatter_output_df[strong_words_scatter_output_df["buzz_type"] == "低反応型"].head(1)
        df = pd.concat([strong_comments_transcript_video_df, strong_comments_video_df, strong_transcripts_video_df, non_strong_video_df], ignore_index=True)
        for _, row in df.iterrows():
            strong_words_scatter_data.append({
                "video_id": str(row["video_id"]),
                "title": str(row["title"]),
                "buzz_type": str(row["buzz_type"])
            })
        return jsonify(strong_words_scatter_data)
    
    @app.route("/api/analyze_videos/", methods=["GET"])
    # loadCompareVideoOptions()で呼び出される
    # 'output_df' から 'video_id' と 'title' を取り出して、JSONで返す
    def analyze_videos():
        df = output_df.copy()
        df = df[~df["video_id"].isin(["平均", "中央値", "荳ｭ螟ｮ蛟､"])]
        video_data = []

        for _, row in df.iterrows():
            video_data.append({
                "video_id": str(row["video_id"]),
                "title": str(row.get("title", row["video_id"]))
            })

        return jsonify(video_data)
    
    # compareSelectedVideos()から動画IDを含んだURLパラメータを受け取る
    @app.route("/api/analyze_result/", methods=["GET"])
    def analyze_result():
        selected_ids = request.args.getlist("video_id")
        top_n = request.args.get("top_n", default=15, type=int)
        top_n = max(1, min(top_n, 15))

        # 平均行と動画行がセットになっているoutput_dfから、平均行と動画行を分ける
        raw_df = output_df.copy()
        mean_mask = raw_df["video_id"].isin(["平均", "荳ｭ螟ｮ蛟､"])

        # mean_dfは偏差値計算の平均値の基準になる
        mean_df = raw_df[mean_mask]
        df = raw_df[~mean_mask].copy()
        transcript_threshold = df["strong_transcript_score"].quantile(0.75)
        comments_threshold = df["strong_comment_score"].quantile(0.75)

        # 各動画にbuzz_typeを付ける
        df["buzz_type"] = df.apply(classify, args=(transcript_threshold, comments_threshold),axis=1)

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        exclude_cols = [
            "viewCount",
            "likeCount",
            "commentCount",
            "subscriberCount"
        ]
        feature_cols = [
            col for col in numeric_cols
            if col not in exclude_cols
        ]
        # 全特徴量を出すと多すぎるため、shap_importance_df_outputの上位から最大15個に絞る
        shap_feature_cols = []
        for _, row in shap_importance_df_output.head(top_n).iterrows():
            feature_name = row["feature"]
            raw_feature_name = REVERSE_FEATURE_LABELS.get(feature_name, feature_name)
            if raw_feature_name in feature_cols and raw_feature_name not in shap_feature_cols:
                shap_feature_cols.append(raw_feature_name)
        # SHAP側の特徴量名は日本語ラベル化されている場合がある
        # そのため、FEATURE_LABELSを逆引きして、output_dfの元カラム名に戻す(照合用)
        feature_cols = shap_feature_cols or feature_cols[:top_n]
        stds = df[feature_cols].std(numeric_only=True)
        if mean_df.empty:
            means = df[feature_cols].mean(numeric_only=True)
        else:
            means = mean_df.iloc[0][feature_cols]

        # 選択された動画だけに絞る
        selected_df = df[df["video_id"].isin(selected_ids)].copy()
        result_data = []
        
        '''
        {
            "feature": 表示用特徴量名,
            "raw_feature": 元のカラム名,
            "value": 動画の値,
            "mean": 平均,
            "std": 標準偏差,
            "diff": 動画の値 - 平均,
            "deviation": 偏差値
        }
        '''
        for _, row in selected_df.iterrows():
            comparisons = []

            for feature in feature_cols:
                value = row[feature]
                mean = means[feature]
                std = stds[feature]
                deviation = None
                if pd.notna(value) and pd.notna(mean) and pd.notna(std) and std != 0:
                    deviation = ((value - mean) / std) * 10 + 50


                comparisons.append({
                    "feature": FEATURE_LABELS.get(feature, feature),
                    "raw_feature": feature,
                    "value": to_json_number(value),
                    "mean": to_json_number(mean),
                    "std": to_json_number(std),
                    "diff": to_json_number(value - mean),
                    "deviation": to_json_number(deviation)
                })

            result_data.append({
                "video_id": str(row["video_id"]),
                "title": str(row.get("title", row["video_id"])),
                "view_count": to_json_number(row.get("viewCount")),
                "buzz_type": row["buzz_type"],
                "comparisons": comparisons
            })
        return jsonify({
            "features": [FEATURE_LABELS.get(feature, feature) for feature in feature_cols],
            "videos": result_data
        })
