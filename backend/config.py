from datetime import timezone
from datetime import datetime as dt
import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).with_name(".env")

# .envファイルの読み込み
def load_env():
    load_dotenv(ENV_PATH, override=True)

# .envファイルからのyoutube_api_keyの読み込み
def get_youtube_api_key():
    load_env()
    return os.getenv("YOUTUBE_API_KEY")


load_env()
YOUTUBE_API_KEY = get_youtube_api_key()

# transcript取得のproxyの認証データの取得
proxy_username = os.getenv('proxy_username')
proxy_password = os.getenv('proxy_password')

# 動画データ取得のためのconfigの作成
def create_config():
    KEYWORD = "音楽"
    PART = os.getenv("PART", "id,snippet")
    TYPE = os.getenv("TYPE", "video")
    RELEVANCELANGUAGE=os.getenv("RELEVANCELANGUAGE", "ja")
    VIDEOCATEGORYID=os.getenv("VIDEOCATEGORYID", "10")
    now = dt.now(timezone.utc)
    now_midnight = now.replace(hour=0, minute=0, second=0)
    td1 = datetime.timedelta(days=60)
    td2 = datetime.timedelta(days=10)
    target_time1 = now_midnight - td1
    target_time1 = target_time1.strftime("%Y-%m-%dT%H:%M:%SZ")
    target_time2 = now_midnight - td2
    target_time2 = target_time2.strftime("%Y-%m-%dT%H:%M:%SZ")

    # genresとcontextsを組み合わせて検索ワード群を作成
    genres = [
    "J-POP",
    "ロック",
    "バンド",
    "アイドル",
    "VTuber 音楽",
    "アニソン",
    "ボカロ",
    "歌い手",
    ]
    contexts = [
    "Music Video",
    "Official Video",
    "歌ってみた",
    "新曲",
    "弾いてみた",
    "カバー",
    "踊ってみた",
    "ライブ",
    ]
    search_lists = []
    for g in genres:
        for c in contexts:
            raw_keyword = [f'{g} {c}']
            keyword =  " ".join(raw_keyword)
            search_list = [keyword, PART, TYPE, "relevance", target_time1, RELEVANCELANGUAGE, VIDEOCATEGORYID]
            search_lists.append(search_list)
    # search_list = [[KEYWORD, PART, TYPE, "viewCount", target_time1, RELEVANCELANGUAGE, VIDEOCATEGORYID], 
    #             [KEYWORD, PART, TYPE, "date", target_time2, RELEVANCELANGUAGE, VIDEOCATEGORYID], 
    #             [KEYWORD, PART, TYPE, "relevance", target_time1, RELEVANCELANGUAGE, VIDEOCATEGORYID]]
    return KEYWORD, search_lists
