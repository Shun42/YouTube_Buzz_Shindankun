from datetime import datetime, timezone

import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import get_youtube_api_key


YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube = None
youtube_api_key = None

# HTTPエラーのレスポンスを返す
def _http_error_message(error):
    try:
        return error.content.decode("utf-8")
    except Exception:
        return str(error)

# youtube_apiの起動情報の作成
def get_youtube_client():
    developer_key = get_youtube_api_key()
    if not developer_key:
        raise RuntimeError("YOUTUBE_API_KEY is not set. Check backend/.env.")

    global youtube, youtube_api_key
    if youtube is None or youtube_api_key != developer_key:
        youtube = build(
            YOUTUBE_API_SERVICE_NAME,
            YOUTUBE_API_VERSION,
            developerKey=developer_key,
        )
        youtube_api_key = developer_key
    return youtube

# youtubeの動画データの取得
def youtube_search(youtube, search_list, KEYWORD, max_results=50):
    video_ids = []
    failed_searches = []
    keyword = KEYWORD

    for item in search_list:
        try:
            params = {
                "q": item[0],
                "part": item[1],
                "type": item[2],
                "order": item[3],
                "publishedAfter": item[4],
                "maxResults": max_results,
                "relevanceLanguage": item[5],

            }
            search_request = youtube.search().list(**params)


            search_response = search_request.execute()
            if "items" not in search_response:
                raise RuntimeError("YouTube API response is invalid.")

            for video in search_response["items"]:
                video_id = video.get("id", {}).get("videoId")
                if video_id:
                    video_ids.append(video_id)

        # エラーの例外処理(HTTPレスポンスを返す)
        except HttpError as e:
            message = _http_error_message(e)
            failed_searches.append(f"{item[0]}: {message}")
            print(f"YouTube API search skipped: {item[0]}")
            print(message)
        except Exception as e:
            failed_searches.append(f"{item[0]}: {e}")
            print(f"YouTube API search skipped: {item[0]}")
            print(e)

    video_ids = list(dict.fromkeys(video_ids))
    if not video_ids:
        details = "\n".join(failed_searches[-3:])
        raise RuntimeError(f"YouTube API search returned no videos.\n{details}")

    print(f"取得したビデオの数は{len(video_ids)}です")
    return video_ids, keyword

# 動画の統計データの取得
def get_statistics(video_ids):
    if isinstance(video_ids, str):
        video_ids = [video_ids]

    statistics = []
    for i in range(0, len(video_ids), 50):
        video_id_list = video_ids[i: i + 50]
        video_ids_string = ",".join(video_id_list)
        request_url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "key": get_youtube_api_key(),
            "part": "snippet,statistics",
            "id": video_ids_string,
        }

        statistics_response = requests.get(request_url, params=params, timeout=15)
        statistics_response.raise_for_status()
        statistic = statistics_response.json()
        if "items" not in statistic:
            raise RuntimeError("YouTube API response is invalid.")
        statistics.append(statistic)
    return statistics

# 動画データ、統計データをdfにする
def processing_response(statistics, keyword):
    now = datetime.now(timezone.utc).isoformat()
    raw_video_datas = []

    for statistic in statistics:
        for video in statistic["items"]:
            video_id = video["id"]
            snippet = video["snippet"]
            stats = video["statistics"]
            title = snippet["title"]

            raw_video_datas.append(
                {
                    "videoId": video_id,
                    "title": title,
                    "viewCount": stats.get("viewCount", 0),
                    "likeCount": stats.get("likeCount", 0),
                    "commentCount": stats.get("commentCount", 0),
                    "publishedAt": snippet["publishedAt"],
                    "channelId": snippet["channelId"],
                    "tags": snippet.get("tags", []),
                    "collectedAt": now,
                    "keyword": keyword,
                }
            )

    print(f"raw_video_data count: {len(raw_video_datas)}")
    return raw_video_datas

# チャンネル登録者データを追加で取得
def get_subscribers(items):
    video_datas = []
    collected_at = datetime.now(timezone.utc).isoformat()

    for i in range(0, len(items), 50):
        raw_data_list = items[i: i + 50]
        channel_ids = list({video["channelId"] for video in raw_data_list})
        channel_id_string = ",".join(channel_ids)
        request_url = "https://www.googleapis.com/youtube/v3/channels"
        params = {
            "key": get_youtube_api_key(),
            "part": "statistics",
            "id": channel_id_string,
        }

        statistics_response = requests.get(request_url, params=params, timeout=15)
        statistics_response.raise_for_status()
        channel_data = statistics_response.json()
        if "items" not in channel_data:
            raise RuntimeError("YouTube API response is invalid.")

        subscribers_by_channel_id = {}
        for channel in channel_data["items"]:
            channel_id = channel["id"]
            subscriber = channel["statistics"].get("subscriberCount", 0)
            subscribers_by_channel_id[channel_id] = {
                "subscriberCount": subscriber,
            }

        for video in raw_data_list:
            subscriber_data = subscribers_by_channel_id.get(
                video["channelId"],
                {"subscriberCount": 0},
            )
            video_data = dict(video)
            video_data.update(subscriber_data)
            video_data["collectedAt"] = collected_at
            video_datas.append(video_data)

    print(f"video_data count: {len(video_datas)}")
    return video_datas
