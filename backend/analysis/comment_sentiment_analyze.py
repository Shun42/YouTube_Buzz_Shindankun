import pandas as pd
from asari.api import Sonar
import pycld2
import nltk as nl
from nltk.data import find
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import time
import datetime
_vader_analyzer = None
_sonar_analyzer = None

# 残り時間の推定
def _print_remaining_time(label, starttime, processed_count, total_count):
    if processed_count <= 0 or total_count <= 0:
        return

    elapsed_time = time.time() - starttime
    average_time = elapsed_time / processed_count
    remaining_count = total_count - processed_count
    estimated_remaining_seconds = round(average_time * remaining_count)
    estimated_finish_at = datetime.datetime.now() + datetime.timedelta(seconds=estimated_remaining_seconds)
    estimated_time_minute = estimated_remaining_seconds / 60
    estimated_time_hour = estimated_time_minute / 60
    print(f"{label}の終了予想時刻は{estimated_finish_at:%Y-%m-%d %H:%M:%S}です")
    print(f"{label}の残り処理時間は約{estimated_time_hour:.2f}時間{estimated_time_minute:.2f}分です")

# 英語コメントの感情分析ライブラリのダウンロード
def _get_vader_analyzer():
    global _vader_analyzer

    if _vader_analyzer is None:
        try:
            find("sentiment/vader_lexicon.zip")
        except LookupError:
            nl.download("vader_lexicon", quiet=True)
        _vader_analyzer = SentimentIntensityAnalyzer()

    return _vader_analyzer


def _get_sonar_analyzer():
    global _sonar_analyzer

    if _sonar_analyzer is None:
        _sonar_analyzer = Sonar()

    return _sonar_analyzer

# 言語検知
def language_detect(text):
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return None

    try:
        isReliable, textBytesFound, details = pycld2.detect(text)
    except pycld2.error:
        return None

    language_list = []
    for l in details:
        language_list.append(l[1])
    # =>['ja', 'en', 'un']

    if 'ja' in language_list:
        return "ja"
    elif "en" in language_list:
        return "en"
    else:
        pass

# 日本語のコメントの感情分析
def sentiment_analysis_jp(text):
    sonar = _get_sonar_analyzer()
    analyze_result = sonar.ping(text)
    # 感情極性スコア
    negative_score = analyze_result["classes"][0]["confidence"]
    positive_score = analyze_result["classes"][1]["confidence"]
    return positive_score, negative_score

# 英語のコメントの感情分析
def sentiment_analysis_en(text):
    vader_analyzer = _get_vader_analyzer()

    result = vader_analyzer.polarity_scores(text)
    # 感情極性スコア
    positive_score = (result["compound"] + 1 ) / 2
    negative_score = 1 - positive_score
    return positive_score, negative_score

# 感情分析を行う関数
def sentiment_analyze(comment_df_processed):
    scores_list = []
    df = comment_df_processed
    # 残り時間の推定
    total_data_length = len(df)
    estimate_sample_size = min(100, total_data_length)
    starttime = time.time()
    print(f"comment_sentimentの全体処理件数は{total_data_length}件です")

    for i, text in enumerate(df["text"]):
        if i + 1 == estimate_sample_size:
            _print_remaining_time("comment_sentiment", starttime, estimate_sample_size, total_data_length)
        if i % 1000 == 0:
            print(f"comment_sentimentの{i}番目の言葉の処理を始めます")
        # 言語検知
        language = language_detect(text)
        # 日本語と英語それぞれで感情分析
        if language == "ja":
            scores_list.append(sentiment_analysis_jp(text))
        elif language == "en":
            scores_list.append(sentiment_analysis_en(text))
        else:
            scores_list.append(("none", "none"))


    scores_df = pd.DataFrame(scores_list, columns=["positive_score", "negative_score"])
    df["positive_score"] = scores_df["positive_score"]
    df["negative_score"] = scores_df["negative_score"]
    comment_df = df
    return comment_df
