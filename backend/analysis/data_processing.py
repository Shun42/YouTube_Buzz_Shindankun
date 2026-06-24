import pandas as pd
import numpy as np

# 動画時間を8つにわけて、それぞれにtranscriptがいくつあるか計算
def word_count(df):
    df = df.copy()
    df["wordCount"] = df["transcript"].astype(str).str.len()
    # 各動画の字幕上の終了時刻を動画長として使う
    df["endtime"] = df["starttime"] + df["duration"]
    df["video_duration"] = df.groupby("video_id")["endtime"].transform("max")

    # 動画内の相対位置: 0.0〜1.0
    df["relative_position"] = df["starttime"] / df["video_duration"]

    # 8分割: 0〜7
    df["section"] = (df["relative_position"] * 8).astype(int)

    # ちょうど最後が 8 になるケースを 7 に丸める
    df["section"] = df["section"].clip(0, 7)

    # 表示用に 1〜8 にする
    df["section"] = df["section"] + 1
    df = df.groupby(["video_id", "section"], as_index=False)["wordCount"].sum()
    df["totalWordCount"] = df.groupby("video_id")["wordCount"].transform("sum")
    df["wordCountRate"] = df["wordCount"] / df["totalWordCount"]
    df = df.groupby("section", as_index=False)["wordCountRate"].mean()
    return df

# 外れ値の除去
def outliner_remove(df):
    q1 = df["view_count"].quantile(0.25)
    q3 = df["view_count"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return df[(df["view_count"] >= lower) & (df["view_count"] <= upper)].copy()

# JSで表示する際にjsonで渡す用のdfの加工
def data_process(shap_importance_df, df_unprocessed, conn, raw_transcript_SQL_order, trend_comment_SQL_order, trend_tag_SQL_order, trend_word_SQL_order):
    shap_importance_df_output = shap_importance_df.head(15)
    shap_importance_df_output = shap_importance_df_output[
    ~shap_importance_df_output["feature"].isin(["高評価数", "コメント数", "登録者数"])]
    df_unprocessed = df_unprocessed.drop(columns=["likeCount_norm", "commentCount_norm", "subscriberCount_norm"], errors="ignore")
    
    # 各特徴量を日本語にする
    scatter_df = df_unprocessed.rename(columns={"title": "タイトル", "viewCount": "view_count", "likeCount": "高評価数", "commentCount":"コメント数","subscriberCount": "登録者数", "like_rate": "再生数あたりの高評価率", "comment_rate": "再生数あたりのコメント数",
                        "title_length": "タイトル長", "curiosity_score": "興味を引く単語数(タイトル)", "benefit_score": "ハウツー系単語数(タイトル)", "emotion_score": "感情単語数(タイトル)", "nagative_score": "ネガティブ単語数(タイトル)",
                        "emphasis_score": "強調単語数(タイトル)", "question_flag": "？が含まれているか(タイトル)", "exclamation_count": "！が含まれているか(タイトル)", "has_number": "数字が含まれているか(タイトル)", "cover_flag": "カバー動画かどうか(タイトル)",
                        "trend_score": "トレンドワードの影響度(タイトル)", "tag_count": "動画タグ数", "tags_trend_score": "トレンドワードの影響度(タグ)", "positive_comment_score": "ポジティブ度(コメント)", "negative_comment_score": "ネガティブ度(コメント)", "comment_praise_score" :"賞賛単語数(コメント)",
                        "comment_emotion_score": "感情単語数(コメント)", "comment_surprise_score": "驚き単語数(コメント)", "comment_addiction_score": "中毒単語数(コメント)", "comment_relatable_score": "共感単語数(コメント)", "comment_music_otaku_score": "音楽オタク単語数(コメント)",
                        "comment_viral_score": "バズ単語数(コメント)", "comment_negative_word_score": "ネガティブ単語数(コメント)", "comment_community_score": "ファン単語数(コメント)", "strong_comment_score": "バズ単語数合計(コメント)", "peak_density": "内容が濃い動画箇所",
                        "density_variance": "動画内容の濃さの分散", "max_emotion_section": "ポジティブな単語が最も多い動画箇所", "min_emotion_section": "ネガティブな単語が最も多い動画箇所", "emotion_positive_score": "ポジティブワードの件数", "emotion_negative_score": "ネガティブワードの件数",
                        "surprise_score": "驚き単語数(字幕)", "music_score": "音楽単語数(字幕)", "story_score": "ストーリー単語数(字幕)", "hook_density": "フック部(動画時間30秒まで)の単語数", "words_per_second": "秒ごとの単語数", "emotion_diff": "場面ごとの感情の起伏",
                        "strong_transcript_score": "バズ単語数合計(字幕)"})
    
    # 各trendデータをSQLiteから読み込む
    try:
        raw_transcript_df = pd.read_sql_query(raw_transcript_SQL_order, conn)
        trend_comment_df = pd.read_sql_query(trend_comment_SQL_order, conn)
        trend_tag_df = pd.read_sql_query(trend_tag_SQL_order, conn)
        trend_word_df = pd.read_sql_query(trend_word_SQL_order, conn)
    finally:
        conn.close()
    trend_comment_df = trend_comment_df.drop(columns="collectedAt", errors="ignore")
    trend_tag_df = trend_tag_df.drop(columns="collectedAt", errors="ignore")
    trend_word_df = trend_word_df.drop(columns="collectedAt", errors="ignore")
    df = df_unprocessed.sort_values("viewCount", ascending=False)
    # 50つの動画のデータと、前動画の中央値を同じoutput_dfにする
    df_head = df.head(50).copy()
    mean_row = df.mean(numeric_only=True).to_frame().T
    mean_row = mean_row.reindex(columns=df_head.columns)
    mean_row["video_id"] = "平均"
    output_df = pd.concat([df_head, mean_row], ignore_index=True)

    # 外れ値除去
    scatter_df = outliner_remove(scatter_df)

    # buzz動画だけのbuzz_videos_dfとbuzz出ない動画だけのnon_buzz_videos_dfを作る
    threshold_high_buzz = scatter_df["view_count"].quantile(0.8)
    threshold_non_buzz = scatter_df["view_count"].quantile(0.1)
    buzz_id_df = df.query('viewCount >= @threshold_high_buzz').copy()
    non_buzz_id_df = df.query('viewCount <= @threshold_non_buzz').copy()
    buzz_video_ids = buzz_id_df["video_id"].tolist()
    non_buzz_video_ids = non_buzz_id_df["video_id"].tolist()
    buzz_videos_df = raw_transcript_df[raw_transcript_df["video_id"].isin(buzz_video_ids)].copy()
    non_buzz_videos_df = raw_transcript_df[raw_transcript_df["video_id"].isin(non_buzz_video_ids)].copy()
    buzz_videos_df["starttime"] = buzz_videos_df["starttime"].astype(float)
    non_buzz_videos_df["starttime"] = non_buzz_videos_df["starttime"].astype(float)
    buzz_videos_df["time_bin"] = (buzz_videos_df["starttime"] // 10) * 10
    non_buzz_videos_df["time_bin"] = (non_buzz_videos_df["starttime"] // 10) * 10

    # 動画時間を8つにわけて、それぞれにtranscriptがいくつあるか計算
    buzz_videos_df = word_count(buzz_videos_df)
    non_buzz_videos_df = word_count(non_buzz_videos_df)
    buzz_videos_df.to_csv("backend/data/buzz_videos_df.csv", index=False)
    scatter_df["view_count"] = scatter_df["view_count"].apply(np.log)
    strong_words_scatter_df = df.copy()
    return shap_importance_df_output, scatter_df, buzz_videos_df, non_buzz_videos_df, trend_comment_df, trend_tag_df, trend_word_df, output_df, strong_words_scatter_df
