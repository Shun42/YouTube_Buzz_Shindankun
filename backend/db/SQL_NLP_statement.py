
import os


def _limit_clause(env_name):
    value = os.getenv(env_name)
    if not value:
        return ""

    try:
        limit = int(value)
    except ValueError:
        return ""

    if limit <= 0:
        return ""

    return f"\n    LIMIT {limit}"


# NLP分析をする際のSQL文
def comment_SQL():
    comment_SQL_order = (
    f'''SELECT crd.*
    FROM comment_raw_data AS crd
    WHERE crd.collectedAt = (
        SELECT MAX(collectedAt)
        FROM comment_raw_data
    )
    ORDER BY crd.rowid{_limit_clause("NLP_COMMENT_LIMIT")};
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
    ORDER BY trd.rowid{_limit_clause("NLP_TRANSCRIPT_LIMIT")};
    ''')
    return transcript_SQL_order
