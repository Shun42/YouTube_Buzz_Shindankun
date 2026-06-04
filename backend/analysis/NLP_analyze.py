import pandas as pd
import re
import unicodedata
import ast
import MeCab
import ipadic
from collections import Counter
from JaStopwordFilter import JaStopwordFilter
from datetime import datetime, timezone

# MeCab起動の際の引数
CHASEN_ARGS = r' -F "%m\t%f[7]\t%f[6]\t%F-[0,1,2,3]\t%f[4]\t%f[5]\n"'
CHASEN_ARGS += r' -U "%m\t%m\t%m\t%F-[0,1,2,3]\t\t\n"'

# MeCabで形態素形跡
tagger = MeCab.Tagger(ipadic.MECAB_ARGS + CHASEN_ARGS)

# strong_wordsのdict群
curiosity_dict = {
    "なぜ": 2, "どうして": 2,
    "実は": 2, "真実": 3,
    "衝撃": 3, "驚愕": 3,
    "知らない": 2, "知らなかった": 2,
    "結果": 1, "検証": 2,
    "理由": 2, "原因": 2,
    "裏側": 2, "秘密": 3,
    "正体": 3, "闇": 3,
    "暴露": 3,
    "意外": 2, "まさか": 2
}

benefit_dict = {
    "簡単": 2, "誰でも": 2,
    "最短": 2, "すぐ": 1,
    "上達": 2, "改善": 2,
    "無料": 2, "お得": 2,
    "効率": 2, "時短": 2,
    "初心者": 1, "入門": 1,
    "完全": 1, "徹底": 1,
    "解説": 1, "まとめ": 1,
    "コツ": 2, "ポイント": 1,
    "方法": 1, "やり方": 1
}

emotion_dict = {
    "神": 3, "神曲": 3,
    "最高": 2, "神回": 3,
    "やばい": 2, "ヤバい": 2,
    "えぐい": 3,
    "泣ける": 2, "感動": 2,
    "鳥肌": 3,
    "かっこいい": 2,
    "可愛い": 2,
    "最強": 2,
    "異次元": 3,
    "圧倒的": 2,
}

negative_dict = {
    "失敗": 2,
    "無理": 2,
    "危険": 3,
    "間違い": 2,
    "ダメ": 2,
    "最悪": 3,
    "炎上": 3
}

emphasis_dict = {
    "ガチ": 2,
    "マジ": 2,
    "本気": 2,
    "完全に": 1,
    "絶対": 2
}

# trend_words計算の際の除外ワードリスト
custom_wordlist = ['ライブ', 'official', 'video', 'mv', 'music', '期間', '限定', '公開']

# テキストの正規化
def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    return text

# テキストのトークン化
def tokenize(text):
    node = tagger.parseToNode(text)
    words = []
    while node:
        surface = node.surface
        if surface:
            words.append(surface)
        node = node.next
    return words

# テキスト内のstrong_wordsの数の計算
def calc_score(words, word_dict):
    score = 0
    for word, weight in word_dict.items():
        if any(word in w for w in words):
            score += weight
    return score

# テキスト内に"?"が含まれているか
def has_question(text):
    return int("?" in text or "？" in text)

# テキスト内に"!"が含まれているか
def count_exclamation(text):
    return text.count("!") + text.count("！")

# テキスト内に数字が含まれているか
def has_number(text):
    return int(bool(re.search(r"\d", text)))

# カバー動画かどうか
def is_cover(text):
    keywords = ["cover", "カバー", "歌ってみた", "弾いてみた"]
    return int(any(k in text for k in keywords))

# trend_wordsがいくつ含まれているか
def trend_score(words, trend_words):
    return sum(w in trend_words for w in words)

# trend_tagsがいくつ含まれているか
def trend_tags_score(tags, trend_tags):
    return sum(t in trend_tags for t in tags)

# タイトルのトークン化
def word_parse(title):
    text = normalize_text(title)
    words = tokenize(text)
    return text, words

# タグの標準化
def normalize_tags(tags):
    if isinstance(tags, (list, tuple, set)):
        return [str(tag).strip() for tag in tags if str(tag).strip()]

    if pd.isna(tags):
        return []

    if isinstance(tags, str):
        tags = tags.strip()
        if not tags:
            return []

        try:
            parsed_tags = ast.literal_eval(tags)
        except (ValueError, SyntaxError):
            return [tags]

        if isinstance(parsed_tags, (list, tuple, set)):
            return [str(tag).strip() for tag in parsed_tags if str(tag).strip()]

    return [str(tags).strip()]

# タイトルの特徴量を算出
def extract_title_features(df):
    features = []
    additional_features = []
    all_words = []
    for title in df["title"]:
        text, words = word_parse(title)
        all_words.extend(words)
        

        feature = {
            "title_length": len(text),
            "curiosity_score": calc_score(words, curiosity_dict),
            "benefit_score": calc_score(words, benefit_dict),
            "emotion_score": calc_score(words, emotion_dict),
            "nagative_score": calc_score(words, negative_dict),
            "emphasis_score": calc_score(words, emphasis_dict),
            "question_flag": has_question(text),
            "exclamation_count": count_exclamation(text),
            "has_number": has_number(text),
            "cover_flag": is_cover(text),

        }

        features.append(feature)

    # ストップワードを選定
    filter = JaStopwordFilter(
    convert_full_to_half=True,  
    use_slothlib=False,         
    filter_length=1,          
    use_date=True,             
    use_numbers=True,          
    use_symbols=True,          
    use_spaces=True,           
    use_emojis=True,           
    custom_wordlist=custom_wordlist
    )
    filtered_words = filter.remove(all_words)

    # trend_wordsを算出
    counter = Counter(filtered_words)

    trend_words = counter.most_common(100)
    collected_at = datetime.now(timezone.utc).isoformat()
    for title in df["title"]:
        text, words = word_parse(title)
        additional_feature = {
            "trend_score" : trend_score(words, trend_words),
        }
        additional_features.append(additional_feature)


    feature_df = pd.DataFrame(features)
    additional_feature_df = pd.DataFrame(additional_features)
    trend_title_df = pd.DataFrame(trend_words, columns=["trend_words", "trend_words_count"])
    trend_title_df["collectedAt"] = collected_at
    df = pd.concat([df, feature_df, additional_feature_df], axis=1)
    df.to_excel("backend/data/NLP.xlsx", index=False)
    return df, trend_title_df

# trend_tagsの算出
def extract_tags_features(df):
    tags_features = []
    tags_adittional_features = []
    all_words = []
    for tags in df["tags"]:
        tags = normalize_tags(tags)
        for t, tag in enumerate(tags):
            tag = normalize_text(tag)
            all_words.append(tag)
        tag_count = len(tags)
        tags_feature = {"tag_count": tag_count}
        tags_features.append(tags_feature)

    counter = Counter(all_words)
    trend_tags = counter.most_common(100)

    for tags in df["tags"]:
        tags = normalize_tags(tags)
        tags_additional_feature = {"tags_trend_score": trend_tags_score(tags, trend_tags)}
        tags_adittional_features.append(tags_additional_feature)

    collected_at = datetime.now(timezone.utc).isoformat()
    tags_feature_df = pd.DataFrame(tags_features)
    tags_additional_feature_df = pd.DataFrame(tags_adittional_features)
    trend_tags_df = pd.DataFrame(trend_tags, columns=["trend_tags", "trend_tags_count"])
    trend_tags_df["collectedAt"] = collected_at
    df = pd.concat([df, tags_feature_df, tags_additional_feature_df], axis=1)
    df.to_excel("backend/data/tags_NLP.xlsx", index=False)
    return df, trend_tags_df

