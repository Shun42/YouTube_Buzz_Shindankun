
# NLP分析をする際のSQL文
def comment_SQL():
    comment_SQL_order = (
    '''SELECT crd.*
    FROM comment_raw_data AS crd
    WHERE crd.collectedAt = (
        SELECT MAX(collectedAt)
        FROM comment_raw_data
    );
    ''')
    return comment_SQL_order

def transcript_SQL():
    transcript_SQL_order = (
        '''SELECT trd.*
    FROM transcript_raw_data AS trd
    WHERE trd.collectedAt = (
        SELECT MAX(collectedAt)
        FROM transcript_raw_data
    );
    ''')
    return transcript_SQL_order
