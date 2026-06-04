import pycld2
import re
import MeCab
from collections import Counter
from JaStopwordFilter import JaStopwordFilter
from analysis import comment_strong_words_dict
import pandas as pd
from datetime import datetime, timezone, timedelta
import time

# 処理時間の予測
def _print_remaining_time(label, starttime, processed_count, total_count):
    if processed_count <= 0 or total_count <= 0:
        return

    elapsed_time = time.time() - starttime
    average_time = elapsed_time / processed_count
    remaining_count = total_count - processed_count
    estimated_remaining_seconds = round(average_time * remaining_count)
    estimated_finish_at = datetime.now() + timedelta(seconds=estimated_remaining_seconds)
    estimated_time_minute = estimated_remaining_seconds / 60
    estimated_time_hour = estimated_time_minute / 60
    print(f"{label}の終了予想時刻は{estimated_finish_at:%Y-%m-%d %H:%M:%S}です")
    print(f"{label}の残り処理時間は約{estimated_time_hour:.2f}時間{estimated_time_minute:.2f}分です")

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

# 日本語のNLP分析
def NLP_analysis_jp(text):

    # 記号の除去
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
    target_pos = ["名詞","動詞","形容詞"]
    filtered_tokens = [token for token in tokens if token[1] in target_pos]
    tokens_output = [token[0] for token in filtered_tokens]
    # token単位にして返す
    return ",".join(tokens_output) if tokens_output else "none"

# コメントのNLP分析
def comment_NLP_analyze(comment_df):
    tokens_list = []
    df = comment_df
    # 処理の残り時間の推定
    # 100件またはそれ以下の処理時間から全体の残り時間を推定
    total_data_length = len(df)
    estimate_sample_size = min(100, total_data_length)
    starttime = time.time()
    print(f"comment_NLPの全体処理件数は{total_data_length}件です")

    for i, text in enumerate(df["text"]):
        if i + 1 == estimate_sample_size:
            _print_remaining_time("comment_NLP", starttime, estimate_sample_size, total_data_length)
        if i % 1000 == 0:
            print(f"comment_NLPの{i}番目の言葉の処理を始めます")
        # 言語検知
        language = language_detect(text)
        # 日本語のみNLP分析をする
        if language == "ja":
            tokens_list.append(NLP_analysis_jp(text))
        else:
            tokens_list.append("none")
    tokens_list_joined = ','.join(tokens_list)
    tokens_list_processed = tokens_list_joined.split(',')
    # ストップワードの除去
    custom_wordlist = ['none', 'いる', 'こと', 'なる', 'くる']
    filter = JaStopwordFilter(
    convert_full_to_half=True,  # 全角文字を半角文字に変換
    use_slothlib=False,         # SlothLibのストップワードを使用しない
    filter_length=1,           # 文字数が1以下のトークンを削除
    use_date=True,             # 日付形式のトークンを削除
    use_numbers=True,          # 数字のトークンを削除
    use_symbols=True,          # 記号を削除
    use_spaces=True,           # 空白トークンを削除
    use_emojis=True,           # 絵文字を削除
    custom_wordlist=custom_wordlist
    )
    filtered_words = filter.remove(tokens_list_processed)
    # コメント全体の中から頻出単語の割り出し
    c = Counter(filtered_words)	
    trend_comments = c.most_common(100)
    tokens_df = pd.DataFrame(tokens_list, columns=["tokens"])
    trend_comments_df = pd.DataFrame(trend_comments, columns=["trend_comments", "trend_commnets_count"])
    collected_at = datetime.now(timezone.utc).isoformat()
    trend_comments_df["collectedAt"] = collected_at
    df["tokens"] = tokens_df["tokens"]
    df["tokens"] = df["tokens"].fillna("none").astype(str)
    comment_df = df
    comment_df.to_excel("backend/data/comment_df_processed.xlsx", index=False)
    return comment_df, trend_comments_df

# strong_word(バズの原因になりそうな強い言葉)の検知
def comment_strong_word_count(comment_df):
    comment_df["text"] = comment_df["text"].fillna("none").astype(str)
    feature_list = []
    for text in comment_df["text"]:
        feature_dict = {
            "comment_praise_score": 0,
            "emotion_score": 0,
            "surprise_score": 0,
            "addiction_score": 0,
            "relatable_score": 0,
            "music_otaku_score": 0,
            "viral_score": 0,
            "negative_word_score": 0,
            "community_score": 0
        }
        # それぞれのカテゴリのstrong_wordの検知
        for word, score in comment_strong_words_dict.praise.items():
            feature_dict["comment_praise_score"] += text.count(word) * score
        for word, score in comment_strong_words_dict.emotion.items():
            feature_dict["emotion_score"] += text.count(word) * score
        for word, score in comment_strong_words_dict.surprise.items():
            feature_dict["surprise_score"] += text.count(word) * score
        for word, score in comment_strong_words_dict.addiction.items():
            feature_dict["addiction_score"] += text.count(word) * score
        for word, score in comment_strong_words_dict.relatable.items():
            feature_dict["relatable_score"] += text.count(word) * score
        for word, score in comment_strong_words_dict.music_otaku.items():
            feature_dict["music_otaku_score"] += text.count(word) * score 
        for word, score in comment_strong_words_dict.viral.items():
            feature_dict["viral_score"] += text.count(word) * score  
        for word, score in comment_strong_words_dict.negative.items():
            feature_dict["negative_word_score"] += text.count(word) * score
        for word, score in comment_strong_words_dict.community.items():
            feature_dict["community_score"] += text.count(word) * score
        feature_list.append(feature_dict)
    wordcount_df = pd.DataFrame(feature_list, columns=["comment_praise_score", "emotion_score", "surprise_score", "addiction_score", "relatable_score", "music_otaku_score", 
                                                    "viral_score", "negative_word_score", "community_score"])
    # それぞれのstrong_wordの数の合計(strong_comment_score)の計算
    wordcount_df["strong_comment_score"] = (
        wordcount_df["comment_praise_score"]
        + wordcount_df["emotion_score"]
        + wordcount_df["surprise_score"]
        + wordcount_df["addiction_score"]
        + wordcount_df["relatable_score"]
        + wordcount_df["music_otaku_score"]
        + wordcount_df["viral_score"]
        + wordcount_df["negative_word_score"]
        + wordcount_df["community_score"]
    )
    return comment_df.join(wordcount_df)
