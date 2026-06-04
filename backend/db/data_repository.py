import json
import pandas as pd
# データをチャンクごとに小分けにしてSQLに格納
def _to_sql_in_chunks(df, table_name, conn, if_exists="append", max_sql_variables=900):
    chunksize = max(1, max_sql_variables // max(1, len(df.columns)))
    df.to_sql(
        table_name,
        conn,
        if_exists=if_exists,
        index=None,
        method="multi",
        chunksize=chunksize,
    )

# 取得したraw_dataを格納
def raw_data_storing(conn, df, comment_df, transcript_df, trend_words_df, trend_tags_df, trend_comments_df):
    df['tags'] = df["tags"].apply(lambda tag: json.dumps(tag, ensure_ascii=False))
    df.to_csv("backend/data/raw_video_data.csv", index=False)
    comment_df.to_csv("backend/data/raw_comment_data.csv", index=False)
    transcript_df.to_csv("backend/data/raw_transcript_data.csv", index=False)
    trend_words_df.to_csv("backend/data/trend_words_data.csv", index=False)
    trend_tags_df.to_csv("backend/data/trend_tags_data.csv", index=False)
    trend_comments_df.to_csv("backend/data/trend_comments_data.csv", index=False)
    _to_sql_in_chunks(df, "youtube_data", conn)
    _to_sql_in_chunks(comment_df, "comment_raw_data", conn)
    _to_sql_in_chunks(transcript_df, "transcript_raw_data", conn)
    trend_words_df.to_sql('trend_word_data', conn, if_exists="append", index=None, method='multi')
    trend_tags_df.to_sql('trend_tag_data', conn, if_exists="append", index=None, method='multi')
    trend_comments_df.to_sql('trend_comment_data', conn, if_exists="append", index=None, method='multi')
    conn.close()


# NLP分析モードで分析するデータを取りだす
def data_extracting(conn, comment_SQL_order, transcript_SQL_order):
    comment_df = pd.read_sql_query(comment_SQL_order, conn)
    transcript_df = pd.read_sql_query(transcript_SQL_order, conn)
    return comment_df, transcript_df

# NLP分析モードで分析したデータを再格納
def processed_data_storing(conn, comment_df, transcript_df):
    comment_df.to_csv("backend/data/comment_data.csv", index=False)
    transcript_df.to_csv("backend/data/transcript_data.csv", index=False)
    _to_sql_in_chunks(comment_df, "comment_data", conn)
    _to_sql_in_chunks(transcript_df, "transcript_data", conn)