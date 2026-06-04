import sqlite3
import sys
# SQLiteに接続
def get_connection():
    try:
        conn = sqlite3.connect("backend/data/youtube.db")
        return conn
    except Exception:
        print("データベース接続でエラーが発生しました")
        sys.exit()