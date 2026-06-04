import requests
import datetime
from config import get_youtube_api_key
import pandas as pd
# コメントのdfのカラム
COMMENT_COLUMNS = [
    "comment_id",
    "video_id",
    "channel_id",
    "text",
    "author_name",
    "author_channel_id",
    "like_count",
    "published_at",
    "updated_at",
    "reply_count",
    "collectedAt",
]

# HTTPエラーのレスポンスを返す
def _youtube_error_reason(response_json):
    try:
        return response_json["error"]["errors"][0]["reason"]
    except (KeyError, IndexError, TypeError):
        return response_json.get("error", {}).get("message", "unknown error")

# コメントデータを取得
def get_comments(video_Ids):
    if type(video_Ids) == str:
        video_Ids = [video_Ids]
    failed_video_ids = []
    raw_comments = []
    for video_Id in video_Ids:
        url = 'https://www.googleapis.com/youtube/v3/'
        resource = 'commentThreads'
        request_url = url + resource
        params = {
        'key': get_youtube_api_key(),
        'part': 'snippet',
        'videoId': video_Id,
        'maxResults': 30
        }
        
        comment_response = requests.get(request_url, params=params, timeout=15)
        comment = comment_response.json()
        # エラーが「この動画ではコメントが有効になっていない」なら無視して続行
        if comment_response.status_code != 200:
            reason = _youtube_error_reason(comment)

            if reason in ("commentsDisabled", "disabledComments"):
                failed_video_ids.append(video_Id)
                continue

            raise RuntimeError(f"Unexpected YouTube API error: {reason}")
        raw_comments.append(comment)
    return raw_comments

# コメントの統計データを取得
def processing_comments_response(raw_comments):
    now = datetime.datetime.now()
    comments_data = []
    for threads in raw_comments:
        for thread in threads.get("items", []):
            top_comment = thread["snippet"]["topLevelComment"]
            top_snippet = top_comment["snippet"]

            comment_data = {
                "comment_id": top_comment["id"],
                "video_id": thread["snippet"]["videoId"],
                "channel_id": thread["snippet"]["channelId"],
                "text": top_snippet["textOriginal"],
                "author_name": top_snippet["authorDisplayName"],
                "author_channel_id": top_snippet["authorChannelId"]["value"],
                "like_count": top_snippet["likeCount"],
                "published_at": top_snippet["publishedAt"],
                "updated_at": top_snippet["updatedAt"],
                "reply_count": thread["snippet"]["totalReplyCount"],
                "collectedAt": now,
            }
            comments_data.append(comment_data)
    comment_df = pd.DataFrame(comments_data, columns=COMMENT_COLUMNS)
    comment_df.to_csv("backend/data/comment_processed.csv", index=False)
    return comment_df
