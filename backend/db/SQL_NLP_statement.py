# NLP分析をする際のSQL文
def comment_SQL():
    comment_SQL_order = (
    f'''SELECT crd.*
    FROM comment_raw_data AS crd
    WHERE crd.collectedAt = (
        SELECT MAX(collectedAt)
        FROM comment_raw_data
    )
    ORDER BY crd.rowid;
    ''')
    return comment_SQL_order

def transcript_SQL():
    transcript_SQL_order = (
        f'''SELECT trd.*
    FROM transcript_raw_data AS trd
    WHERE trd.collectedAt = (
        SELECT MAX(collectedAt)
        FROM transcript_raw_data
    )
    ORDER BY trd.rowid;
    ''')
    return transcript_SQL_order
