import pandas as pd
import datetime
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable
from config import proxy_username, proxy_password
from youtube_transcript_api.proxies import WebshareProxyConfig


TRANSCRIPT_COLUMNS = ["video_id", "transcript", "starttime", "duration", "collectedAt"]
MAX_RETRIES = 5

# APIで返ってきたデータから必要なデータを抽出
def _transcript_row_value(row, key):
    if isinstance(row, dict):
        return row[key]
    return getattr(row, key)

# transcipt_apiでデータ取得
def get_transcript(video_ids):
    now = datetime.datetime.now()
    proxy_config = None
    # プロキシサーバーのユーザーデータがあれば使用
    if proxy_username and proxy_password:
        proxy_config = WebshareProxyConfig(
            proxy_username=proxy_username,
            proxy_password=proxy_password,
        )
    api = YouTubeTranscriptApi(proxy_config=proxy_config)

    # 動画でtranscriptが有効になっていないなどのエラーは無視して続行
    skip_errors = (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable)
    
    all_rows = []

    # 失敗してもMAX_RETRIESの回数まで再実行
    for index, video_id in enumerate(video_ids):
        retry = 0

        while retry < MAX_RETRIES:

            try:
                transcript = api.fetch(video_id, languages=["ja", "en"])

                print(f"success: {video_id}")

                for row in transcript:
                    text = _transcript_row_value(row, "text")
                    if not text.strip().startswith("["):
                        all_rows.append({
                            "video_id": video_id,
                            "transcript": _transcript_row_value(row, "text"),
                            "starttime": _transcript_row_value(row, "start"),
                            "duration": _transcript_row_value(row, "duration"),
                            "collectedAt": now
                        })
                break

            except skip_errors as e:
                print(f"skip: {video_id}")
                print(e)
                break

            except Exception as e:
                retry += 1

                print(f"retry {retry}: {video_id}")
                print(e)




    df = pd.DataFrame(all_rows, columns=TRANSCRIPT_COLUMNS)

    return df
