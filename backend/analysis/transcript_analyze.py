import pandas as pd
import pandas as pd
import pycld2
import re
import MeCab
import spacy
import numpy as np
from asari.api import Sonar
import pycld2
import nltk as nl
from nltk.data import find
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from analysis import strong_words_dict
import datetime
import time

# transcriptの特徴量のタイトル
TRANSCRIPT_FEATURE_COLUMNS = [
    "video_id",
    "peak_density",
    "density_variance",
    "max_emotion_section",
    "min_emotion_section",
    "emotion_positive_score",
    "emotion_negative_score",
    "surprise_score",
    "music_score",
    "story_score",
    "hook_density",
    "collectedAt",
    "words_per_second",
    "emotion_diff",
    "strong_transcript_score",
]

# 処理残り時間の算出
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

# 言語検出
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

# 日本語のNLP分析
def NLP_analysis_jp(text):
    # 記号などの除去
    replaced_text = text.lower()
    replaced_text = re.sub(r'[【】]', ' ', replaced_text)       
    replaced_text = re.sub(r'[（）()]', ' ', replaced_text)     
    replaced_text = re.sub(r'[［］\[\]]', ' ', replaced_text)   
    replaced_text = re.sub(r'[@＠]\w+', '', replaced_text)  
    replaced_text = re.sub(r'\d+\.*\d*', '', replaced_text)
    # MeCabで形態素解析
    mecab = MeCab.Tagger()
    nodes = mecab.parseToNode(replaced_text)
    tokens = []
    while nodes:
        if nodes.surface != "":
            tokens.append([nodes.surface, nodes.feature.split(',')[0]])
        nodes = nodes.next
    # 名詞、動詞、形容詞のみ分析
    target_pos = ["名詞","動詞","形容詞"]
    filtered_tokens = [token for token in tokens if token[1] in target_pos]
    tokens_output = [token[0] for token in filtered_tokens]
    if len(tokens_output) >= 1:
        tokens_output = ','.join(tokens_output)
    return tokens_output



# 英語のNLP分析
def NLP_analysis_en(text):
    global _spacy_nlp

    if _spacy_nlp is None:
        _spacy_nlp = spacy.load('en_core_web_sm')

    tokens = []
    doc = _spacy_nlp(text)
    target_pos = ["ADJ","NOUN","PROPN","VERB"]
    for token in doc:
        if token.pos_ in target_pos:
            tokens.append([str(token), token.pos_])
    filtered_tokens = [token for token in tokens if token[1] in target_pos]
    tokens_output = [token[0] for token in filtered_tokens]
    if len(tokens_output) >= 1:
        tokens_output = ','.join(tokens_output)
    return tokens_output

# video_idごとに最も格納された時間が遅いデータを読み込み
def transcript_SQL():
    transcript_SQL_order = (
    '''SELECT td.*
    FROM transcript_data AS td
    JOIN (
        SELECT video_id, MAX(collectedAt) AS latest_collectedAt
        FROM transcript_data
        GROUP BY video_id
        ) AS latest
    ON td.video_id = latest.video_id
    AND td.collectedAt = latest.latest_collectedAt;
    ''')
    return transcript_SQL_order


_vader_analyzer = None
_sonar_analyzer = None
_spacy_nlp = None

# vader_analyzerの起動
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

# 日本語のセンチメント分析
def sentiment_analysis_jp(text):
    sonar = _get_sonar_analyzer()
    analyze_result = sonar.ping(text)
    negative_score = analyze_result["classes"][0]["confidence"]
    positive_score = analyze_result["classes"][1]["confidence"]
    return positive_score, negative_score

# 英語のセンチメント分析
def sentiment_analysis_en(text):
    vader_analyzer = _get_vader_analyzer()

    result = vader_analyzer.polarity_scores(text)
    # 感情極性スコア
    positive_score = (result["compound"] + 1 ) / 2
    negative_score = 1 - positive_score
    return positive_score, negative_score

# センチメント分析
def sentiment_analyze(df):
    scores_list = []
    # 処理の予想時間の計算
    total_data_length = len(df)
    estimate_sample_size = min(100, total_data_length)
    starttime = time.time()
    print(f"transcript_sentimentの全体処理件数は{total_data_length}件です")

    for i, text in enumerate(df["transcript"]):
        if i + 1 == estimate_sample_size:
            _print_remaining_time("transcript_sentiment", starttime, estimate_sample_size, total_data_length)
        if i % 1000 == 0:
            print(f"transcript_sentimentの{i}番目の言葉の処理を始めます")
        # 言語ごとにセンチメント分析
        language = language_detect(text)
        if language == "ja":
            scores_list.append(sentiment_analysis_jp(text))
        elif language == "en":
            scores_list.append(sentiment_analysis_en(text))
        else:
            scores_list.append((np.nan, np.nan))
    scores_df = pd.DataFrame(scores_list, columns=["positive_score", "negative_score"])
    df["positive_score"] = scores_df["positive_score"]
    df["negative_score"] = scores_df["negative_score"]
    return df

# transcriptごとに単語の数を計算
def word_count(df):
    word_count_list = []
    for text in df["transcript"]:
        word_count_list.append(len(text))
    wordcount_df = pd.DataFrame(word_count_list, columns=["wordCount"])
    df["wordCount"] = wordcount_df["wordCount"]
    return df

# transcriptのstrong_wordの数を計算
def strong_word_count(df):
    feature_list = []
    for text in df["transcript"]:
        feature_dict = {
            "emotion_positive_score": 0,
            "emotion_negative_score": 0,
            "surprise_score": 0,
            "music_score": 0,
            "story_score": 0
        }
        for word, score in strong_words_dict.emotion_positive.items():
            feature_dict["emotion_positive_score"] += text.count(word) * score
        for word, score in strong_words_dict.emotion_negative.items():
            feature_dict["emotion_negative_score"] += text.count(word) * score
        for word, score in strong_words_dict.surprise.items():
            feature_dict["surprise_score"] += text.count(word) * score
        for word, score in strong_words_dict.music.items():
            feature_dict["music_score"] += text.count(word) * score
        for word, score in strong_words_dict.story.items():
            feature_dict["story_score"] += text.count(word) * score
        feature_list.append(feature_dict)
    wordcount_df = pd.DataFrame(feature_list, columns=["emotion_positive_score", "emotion_negative_score", "surprise_score", "music_score", "story_score"])
    return df.join(wordcount_df)


# transcriptのNLP処理
def transcript_NLP_analyze(transcript_df):
    tokens_list = []
    df = transcript_df
    if df.empty:
        df["tokens"] = pd.Series(dtype="object")
        return df
    # 処理にかかる時間の推計
    total_data_length = len(df)
    estimate_sample_size = min(100, total_data_length)
    starttime = time.time()
    print(f"transcript_NLPの全体処理件数は{total_data_length}件です")
    for i, text in enumerate(df["transcript"]):
        if i + 1 == estimate_sample_size:
            _print_remaining_time("transcript_NLP", starttime, estimate_sample_size, total_data_length)
        if i % 1000 == 0:
            print(f"transcript_NLPの{i}番目の言葉の処理を始めます")
        # 言語ごとにNLP処理
        language = language_detect(text)
        if language == "ja":
            tokens_list.append(NLP_analysis_jp(text))
        elif language == "en":
            tokens_list.append(NLP_analysis_en(text))
        else:
            tokens_list.append("none")

    tokens_df = pd.DataFrame(tokens_list, columns=["tokens"])
    df["tokens"] = tokens_df["tokens"]
    df["tokens"] = df["tokens"].fillna("none").astype(str)
    transcript_df = df
    return transcript_df
# transcriptのセンチメント分析
def transcript_analyze(transcript_df):
    df = transcript_df
    if df.empty:
        transcript_features_df = pd.DataFrame(columns=TRANSCRIPT_FEATURE_COLUMNS)
        transcript_features_df.to_csv("backend/data/transcript_features.csv")
        return transcript_features_df
    # 処理時間の推計
    total_data_length = len(df)
    starttime = time.time()
    print(f"transcript_analyzeの全体処理件数は{total_data_length}件です")

    df = df.astype({"starttime": float, "duration": float})
    _print_remaining_time("transcript_analyze", starttime, 1, 6)
    df = sentiment_analyze(df)
    _print_remaining_time("transcript_analyze", starttime, 2, 6)
    df = word_count(df)
    _print_remaining_time("transcript_analyze", starttime, 3, 6)
    df = strong_word_count(df)
    _print_remaining_time("transcript_analyze", starttime, 4, 6)
    # 動画時間10秒ごとにtime_binを設定
    df["time_bin"] = (df["starttime"] // 10) * 10

    df.to_csv("backend/data/transcript.csv")

    # video_id、time_binごとに特徴量を計算
    grouped_df = df.groupby(["video_id", "time_bin"], as_index=False).agg({
        "emotion_positive_score": "sum",
        "emotion_negative_score": "sum",
        "surprise_score": "sum",
        "music_score": "sum",
        "story_score": "sum",
        "wordCount": "sum",
        "positive_score": "mean",
        "negative_score": "mean",
    })
    # フック部(動画の導入部)にどれだけ単語が詰まっているか
    hook_density_df = (
        grouped_df[
            (grouped_df["time_bin"] >= 0)
            & (grouped_df["time_bin"] < 30)
        ]
        .groupby("video_id", as_index=False)["wordCount"]
        .sum()
        .rename(columns={"wordCount": "hook_density"})
    )
    # transcriptの特徴量
    transcript_features_df = grouped_df.groupby("video_id", as_index=False).agg(
        peak_density=("wordCount", "max"),
        total_words=("wordCount", "sum"),
        max_time_bin=("time_bin", "max"),
        density_variance=("wordCount", "var"),
        max_emotion_section=("positive_score", "max"),
        min_emotion_section=("negative_score", "max"),
        emotion_positive_score=("emotion_positive_score", "sum"),
        emotion_negative_score=("emotion_negative_score", "sum"),
        surprise_score=("surprise_score", "sum"),
        music_score=("music_score", "sum"),
        story_score=("story_score", "sum")
        )
    _print_remaining_time("transcript_analyze", starttime, 5, 6)

    transcript_features_df = transcript_features_df.merge(
        hook_density_df,
        on="video_id",
        how="left"
    )
    # 各特徴量の型をfloatに
    transcript_features_df["hook_density"] = transcript_features_df["hook_density"].fillna(0).astype(float)
    transcript_features_df["emotion_positive_score"] = transcript_features_df["emotion_positive_score"].astype(float)
    transcript_features_df["emotion_negative_score"] = transcript_features_df["emotion_negative_score"].astype(float)
    transcript_features_df["surprise_score"] = transcript_features_df["surprise_score"].astype(float)
    transcript_features_df["music_score"] = transcript_features_df["music_score"].astype(float)
    transcript_features_df["story_score"] = transcript_features_df["story_score"].astype(float)
    transcript_features_df["peak_density"] = transcript_features_df["peak_density"].astype(float)
    transcript_features_df["collectedAt"] = datetime.datetime.now()
    # 一秒ごとにいくつ単語があるのか
    transcript_features_df["words_per_second"] = (
        transcript_features_df["total_words"]
        / (transcript_features_df["max_time_bin"] + 10)
    ).astype(float)
    transcript_features_df["density_variance"] = transcript_features_df["density_variance"].fillna(0).astype(float)
    transcript_features_df["max_emotion_section"] = transcript_features_df["max_emotion_section"].astype(float)
    transcript_features_df["min_emotion_section"] = transcript_features_df["min_emotion_section"].astype(float)
    # 最もポジティブな単語が並ぶ個所と最もポジティブな単語が並ぶ個所のポジティブ度の差
    transcript_features_df["emotion_diff"] = (
        transcript_features_df["max_emotion_section"]
        - transcript_features_df["min_emotion_section"]
    ).astype(float)
    # strong_wordsの合計
    transcript_features_df["strong_transcript_score"] = (
        transcript_features_df["emotion_positive_score"]
        + transcript_features_df["emotion_negative_score"]
        + transcript_features_df["surprise_score"]
        + transcript_features_df["music_score"]
        + transcript_features_df["story_score"]
    )
    transcript_features_df = transcript_features_df.drop(columns=["total_words", "max_time_bin"])
    transcript_features_df.to_csv("backend/data/transcript_features.csv")
    _print_remaining_time("transcript_analyze", starttime, 6, 6)
    return transcript_features_df
