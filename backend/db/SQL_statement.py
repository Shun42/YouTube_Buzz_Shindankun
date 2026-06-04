
# 分析モードの際のSQL文
# 動画IDごとに格納された日時が最新のデータを取りだす
def video_SQL():
    video_SQL_order = ('''
    SELECT yd.*
    FROM youtube_data AS yd
    JOIN (
        SELECT videoId, MAX(collectedAt) AS latest_collectedAt
        FROM youtube_data
        GROUP BY videoId
    ) AS latest
    ON yd.videoId = latest.videoId
    AND yd.collectedAt = latest.latest_collectedAt;
    ''')
    return video_SQL_order

def comment_SQL():
    comment_SQL_order = (
    '''SELECT cd.*
    FROM comment_data AS cd
    JOIN (
        SELECT video_id, MAX(collectedAt) AS latest_collectedAt
        FROM comment_data
        GROUP BY video_id
        ) AS latest
    ON cd.video_id = latest.video_id
    AND cd.collectedAt = latest.latest_collectedAt;
    ''')
    return comment_SQL_order

def transcript_SQL():
    transcript_SQL_order = (
    '''SELECT td.*
    FROM transcript_data AS td
    JOIN (
        SELECT video_id, MAX(collectedAt) AS latest_collectedAt
        FROM transcript_data
        GROUP BY video_id
        ) AS latest
    ON td.video_id = latest.video_id
    AND td.collectedAt = latest.latest_collectedAt;
    ''')
    return transcript_SQL_order

# 格納された日時が最新のデータを取りだす
def trend_comment_SQL():
    trend_comment_SQL_order = ('''
    SELECT tcd.*
    FROM trend_comment_data AS tcd
    JOIN (
        SELECT MAX(collectedAt) AS latest_collectedAt
        FROM trend_comment_data
    ) AS latest
    ON tcd.collectedAt = latest.latest_collectedAt;
    ''')
    return trend_comment_SQL_order

def trend_tag_SQL():
    trend_tag_SQL_order = ('''
    SELECT ttd.*
    FROM trend_tag_data AS ttd
    JOIN (
        SELECT MAX(collectedAt) AS latest_collectedAt
        FROM trend_tag_data
    ) AS latest
    ON ttd.collectedAt = latest.latest_collectedAt;
    ''')
    return trend_tag_SQL_order

def trend_word_SQL():
    trend_word_SQL_order = ('''
    SELECT twd.*
    FROM trend_word_data AS twd
    JOIN (
        SELECT MAX(collectedAt) AS latest_collectedAt
        FROM trend_word_data
    ) AS latest
    ON twd.collectedAt = latest.latest_collectedAt;
    ''')
    return trend_word_SQL_order