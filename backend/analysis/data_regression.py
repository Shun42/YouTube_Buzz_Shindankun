import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_squared_log_error
import lightgbm as lgb
import matplotlib
matplotlib.use("Agg")
import shap

TARGET_COLUMN = "viewCount"
MODEL_DROP_COLUMNS = [
    "video_id",
    "max_emotion_section",
    "min_emotion_section",
    "peak_density",
    "collectedAt",
]
FEATURE_LABELS = {
    "likeCount_norm": "高評価数",
    "commentCount_norm": "コメント数",
    "subscriberCount_norm": "登録者数",
    "like_rate": "再生数あたりの高評価率",
    "comment_rate": "再生数あたりのコメント数",
    "title_length": "タイトル長",
    "curiosity_score": "興味を引く単語数(タイトル)",
    "benefit_score": "ハウツー系単語数(タイトル)",
    "emotion_score": "感情単語数(タイトル)",
    "nagative_score": "ネガティブ単語数(タイトル)",
    "emphasis_score": "強調単語数(タイトル)",
    "question_flag": "？が含まれているか(タイトル)",
    "exclamation_count": "！が含まれているか(タイトル)",
    "has_number": "数字が含まれているか(タイトル)",
    "cover_flag": "カバー動画かどうか(タイトル)",
    "trend_score": "トレンドワードの影響度(タイトル)",
    "tag_count": "動画タグ数",
    "tags_trend_score": "トレンドワードの影響度(タグ)",
    "positive_comment_score": "ポジティブ度(コメント)",
    "negative_comment_score": "ネガティブ度(コメント)",
    "comment_praise_score": "賞賛単語数(コメント)",
    "comment_emotion_score": "感情単語数(コメント)",
    "comment_surprise_score": "驚き単語数(コメント)",
    "comment_addiction_score": "中毒単語数(コメント)",
    "comment_relatable_score": "共感単語数(コメント)",
    "comment_music_otaku_score": "音楽オタク単語数(コメント)",
    "comment_viral_score": "バズ単語数(コメント)",
    "comment_negative_word_score": "ネガティブ単語数(コメント)",
    "comment_community_score": "ファン単語数(コメント)",
    "strong_comment_score": "バズ単語数合計(コメント)",
    "peak_density": "内容が濃い動画箇所",
    "density_variance": "動画内容の濃さの分散",
    "max_emotion_section": "ポジティブな単語が最も多い動画箇所",
    "min_emotion_section": "ネガティブな単語が最も多い動画箇所",
    "emotion_positive_score": "ポジティブワードの件数",
    "emotion_negative_score": "ネガティブワードの件数",
    "surprise_score": "驚き単語数(字幕)",
    "music_score": "音楽単語数(字幕)",
    "story_score": "ストーリー単語数(字幕)",
    "hook_density": "フック部(動画時間30秒まで)の単語数",
    "words_per_second": "秒ごとの単語数",
    "emotion_diff": "場面ごとの感情の起伏",
    "strong_transcript_score": "バズ単語数合計(字幕)",
}

# データを機械学習に渡す前の前処理
def _prepare_model_data(feature_df, feature_df_unprocessed):
    df_unprocessed = feature_df_unprocessed.drop(columns=["peak_density"], errors="ignore")
    df = feature_df.drop(columns=MODEL_DROP_COLUMNS, errors="ignore")
    df = df.replace([np.inf, -np.inf], 0)
    df = df.fillna(0)
    return df, df_unprocessed

# 目的変数と特徴量の設定
def _split_features_target(df):
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Required target column '{TARGET_COLUMN}' was not found.")
    df_x = df.drop(TARGET_COLUMN, axis=1)
    df_y = df[TARGET_COLUMN]
    return df_x, df_y

# SHAP値を計算してJSに渡しやすいようにdfにする
def _shap_importance_df(model, x_test, background_data=None):
    if background_data is None:
        explainer = shap.TreeExplainer(model)
    else:
        explainer = shap.TreeExplainer(model, background_data)
    shap_values = explainer.shap_values(x_test, check_additivity=False)
    return pd.DataFrame({
        "feature": x_test.columns,
        "importance": np.abs(shap_values).mean(axis=0)
    }).sort_values("importance", ascending=False)

# 機械学習に渡す前のデータの前処理
def data_preprocessing(conn, video_SQL_order, comment_SQL_order, transcript_SQL_order):
    # SQLiteから各データを呼び出し
    video_df = pd.read_sql_query(video_SQL_order, conn)
    comment_df = pd.read_sql_query(comment_SQL_order, conn)
    transcript_df = pd.read_sql_query(transcript_SQL_order, conn)
    # 各データの前処理
    comment_df = comment_df.replace({"none": 0})
    comment_df = comment_df.astype({'positive_score': 'float', 'negative_score': 'float'})
    video_df = video_df.rename(columns={'videoId': 'video_id'})
    video_df_unprocessed = video_df.drop(columns=["publishedAt", "channelId", "tags", "collectedAt", "viewCount_norm", "buzz_score", "keyword"], errors="ignore")
    video_df = video_df.drop(columns=["title", "publishedAt", "channelId", "tags", "collectedAt", "likeCount", "viewCount_norm", "commentCount", "subscriberCount", "buzz_score", "keyword"], errors="ignore")
    comment_df = comment_df.groupby("video_id", as_index=False).agg(
        positive_comment_score=('positive_score', "mean"),
        negative_comment_score=('negative_score', "mean"),
        comment_praise_score=("comment_praise_score", "sum"),
        comment_emotion_score=("emotion_score", "sum"),
        comment_surprise_score=("surprise_score", "sum"),
        comment_addiction_score=("addiction_score", "sum"),
        comment_relatable_score=("relatable_score", "sum"),
        comment_music_otaku_score=("music_otaku_score", "sum"),
        comment_viral_score=("viral_score", "sum"),
        comment_negative_word_score=("negative_word_score", "sum"),
        comment_community_score=("community_score", "sum"),
        strong_comment_score=("strong_comment_score", "sum"),
    )

    transcript_df = transcript_df.drop(columns=["collectedAt"], errors="ignore")
    # 前処理が終わった各dfをmerge
    feature_df = video_df.merge(comment_df, on="video_id").merge(transcript_df, on="video_id")
    feature_df_unprocessed = video_df_unprocessed.merge(comment_df, on="video_id").merge(transcript_df, on="video_id")
    feature_df.to_csv("backend/data/preprocessing.csv", index=False)
    return feature_df, feature_df_unprocessed


# LightGBMによる回帰分析
def lightgbm_regression(feature_df, feature_df_unprocessed):
    df, df_unprocessed = _prepare_model_data(feature_df, feature_df_unprocessed)
    df = df.rename(columns=FEATURE_LABELS)
    df_x, df_y = _split_features_target(df)
    # 訓練用データとテストデータに分ける
    X_train, X_test, y_train, y_test = train_test_split(df_x, df_y, test_size=0.2, random_state=123)

    models = {
        "regression_log1p": {
            "model": lgb.LGBMRegressor(objective="regression"),
            "y_transform": "log1p",
        },
        "poisson": {
            "model": lgb.LGBMRegressor(objective="poisson"),
            "y_transform": None,
        },
        "tweedie": {
            "model": lgb.LGBMRegressor(objective="tweedie"),
            "y_transform": None,
        },
    }
    results = []

    for model_name, model_info in models.items():
        if model_name == "regression_log1p":
            model_name = "通常回帰"
        elif model_name == "poisson":
            model_name = "ポアソン回帰"
        elif model_name == "tweedie":
            model_name = "Tweedie回帰"
        model = model_info["model"]
        y_transform = model_info.get("y_transform", None)

        if y_transform == "log1p":
            model.fit(X_train, np.log1p(y_train))
            y_pred = np.expm1(model.predict(X_test))
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

        y_pred = np.maximum(y_pred, 0)

        rmsle = np.sqrt(mean_squared_log_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        results.append({
            "model_name": model_name,
            "model": model,
            "rmsle": rmsle,
            "mae": mae,
            "r2": r2,
        })

    best_result = min(results, key=lambda x: x["rmsle"])
    best_model = best_result["model"]
    best_model_name = best_result["model_name"]

    print("Best model:", best_model_name)
    print("RMSLE:", best_result["rmsle"])

    models_output = []
    for result in results:
        models_output.append({
            "model_name": result["model_name"],
            "rmsle": float(result["rmsle"]),
            "mae": float(result["mae"]),
            "r2": float(result["r2"]),
        })

    # SHAP値を計算
    shap_importance_df = _shap_importance_df(best_model, X_test)

    best_result_model = {
        "model_name": best_model_name,
        "rmsle": float(best_result["rmsle"]),
        "mae": float(best_result["mae"]),
        "r2": float(best_result["r2"]),
    }

    return shap_importance_df, df_unprocessed, models_output, best_result_model
