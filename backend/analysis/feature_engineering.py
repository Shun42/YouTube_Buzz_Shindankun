import pandas as pd
# 動画データの特徴量計算
def feature_engineering(items):
    df = pd.DataFrame(items)
    df = df.fillna(0)
    df[["likeCount", "viewCount", "commentCount", "subscriberCount"]] = df[["likeCount", "viewCount", "commentCount", "subscriberCount"]].astype(int)
    df["likeCount_norm"] = (df["likeCount"] - df["likeCount"].min()) / (df["likeCount"].max() - df["likeCount"].min())
    df["viewCount_norm"] = (df["viewCount"] - df["viewCount"].min()) / (df["viewCount"].max() - df["viewCount"].min())
    df["commentCount_norm"] = (df["commentCount"] - df["commentCount"].min()) / (df["commentCount"].max() - df["commentCount"].min())
    df["subscriberCount_norm"] = (df["subscriberCount"] - df["subscriberCount"].min()) / (df["subscriberCount"].max() - df["subscriberCount"].min())
    df["like_rate"] = df["likeCount_norm"] / df["viewCount_norm"]
    df["comment_rate"] = df["commentCount_norm"] / df["viewCount_norm"]
    df["buzz_score"] = df["viewCount_norm"] * 0.6 + df["like_rate"] * 0.2 + df["comment_rate"] * 0.2
    df.to_excel("backend/data/processed.xlsx", index=False)
    return df

