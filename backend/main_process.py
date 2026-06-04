import config
from services import youtube_service
from services import comment_service
from services import transcript_service
from analysis import feature_engineering
from analysis import NLP_analyze
from analysis import comment_NLP_analyze
from analysis import comment_sentiment_analyze
from analysis import transcript_analyze
from analysis import data_regression
from analysis import data_processing
from db import SQL_statement
from db import SQL_NLP_statement
from db import database
from db import data_repository

# パイプラインを起動モードごとに定義

# transriptの言語処理
def _process_transcript_data(transcript_df):
    transcript_df = transcript_analyze.transcript_NLP_analyze(transcript_df)
    return transcript_analyze.transcript_analyze(transcript_df)

# コメントの言語処理
def _process_comment_data(comment_df):
    comment_df = comment_sentiment_analyze.sentiment_analyze(comment_df)
    comment_df = comment_NLP_analyze.comment_strong_word_count(comment_df)
    return comment_df

# 起動モードがデータ収集だった場合のパイプライン
def collect():
    KEYWORD, search_list = config.create_config()
    youtube = youtube_service.get_youtube_client()
    video_ids, keyword = youtube_service.youtube_search(youtube, search_list, KEYWORD)
    statistics = youtube_service.get_statistics(video_ids)
    raw_video_datas = youtube_service.processing_response(statistics, keyword)
    video_datas = youtube_service.get_subscribers(raw_video_datas)
    raw_comments = comment_service.get_comments(video_ids)
    comment_df = comment_service.processing_comments_response(raw_comments)
    df = feature_engineering.feature_engineering(video_datas)
    transcript_df = transcript_service.get_transcript(video_ids)
    df, trend_title_df = NLP_analyze.extract_title_features(df)
    df, trend_tags_df = NLP_analyze.extract_tags_features(df)
    comment_df, trend_comments_df = comment_NLP_analyze.comment_NLP_analyze(comment_df)
    conn = database.get_connection()
    data_repository.raw_data_storing(conn, df, comment_df, transcript_df, trend_title_df, trend_tags_df, trend_comments_df)

# 起動モードがNLP分析だった場合のパイプライン
def NLP_processing():
    conn = database.get_connection()
    try:
        comment_SQL_order = SQL_NLP_statement.comment_SQL()
        transcript_SQL_order = SQL_NLP_statement.transcript_SQL()
        comment_df, transcript_df = data_repository.data_extracting(
            conn,
            comment_SQL_order,
            transcript_SQL_order,
        )
        transcript_df = _process_transcript_data(transcript_df)
        comment_df = _process_comment_data(comment_df)
        data_repository.processed_data_storing(conn, comment_df, transcript_df)
    finally:
        conn.close()


# 起動モードが分析だった場合のパイプライン
def analyze():
    conn = database.get_connection()
    try:
        video_SQL_order = SQL_statement.video_SQL()
        comment_SQL_order = SQL_statement.comment_SQL()
        transcript_SQL_order = SQL_statement.transcript_SQL()
        feature_df, feature_df_unprocessed = data_regression.data_preprocessing(conn, video_SQL_order, comment_SQL_order, transcript_SQL_order)
        raw_transcript_SQL_order = SQL_NLP_statement.transcript_SQL()
        trend_comment_SQL_order = SQL_statement.trend_comment_SQL()
        trend_tag_SQL_order = SQL_statement.trend_tag_SQL()
        trend_word_SQL_order = SQL_statement.trend_word_SQL()
        # shap_importance_df, df_unprocessed = data_regression.randomforest_regression(feature_df, feature_df_unprocessed)
        shap_importance_df, df_unprocessed = data_regression.lightgbm_regression(feature_df, feature_df_unprocessed)
        shap_importance_df_output, scatter_df, buzz_videos_df, non_buzz_videos_df, trend_comment_df, trend_tag_df, trend_word_df, output_df, strong_words_scatter_df = data_processing.data_process(shap_importance_df, df_unprocessed, conn, raw_transcript_SQL_order,
                                                                                                            trend_comment_SQL_order, trend_tag_SQL_order, trend_word_SQL_order)
        # data_processing.export_column_distributions_to_excel(df_unprocessed)

    finally:
        conn.close()
    
    
    return shap_importance_df_output, scatter_df, buzz_videos_df, non_buzz_videos_df, trend_comment_df, trend_tag_df, trend_word_df, output_df, strong_words_scatter_df
