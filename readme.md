# YouTube Buzz Analyzer v2 仕様書

## 1. 概要

本プログラムは、YouTube上の日本音楽系動画を対象に、動画情報、コメント、字幕データを収集し、バズりやすさに関係しそうな特徴量を分析するためのバックエンドアプリケーションです。

主な目的は以下です。

- YouTube Data APIを用いて、日本音楽系動画のメタデータを収集する
- 動画ごとの再生数、評価数、コメント数、チャンネル登録者数を保存する
- コメント、タイトル、タグ、字幕から自然言語特徴量を抽出する
- 機械学習により、再生数やバズ傾向に影響する特徴量を分析する
- Flask画面から収集、NLP処理、分析処理を実行できるようにする

## 2. 全体構成

```text
backend/
  config.py                  YouTube APIキー、検索条件、検索ワードの設定
  main.py                    Flaskアプリの起動ファイル
  main_process.py            収集、NLP処理、分析処理の主要フロー
  background_process.py      バックグラウンド収集・処理用の実行ファイル
  apps/
    app.py                   Flaskアプリ生成
    route.py                 画面遷移、APIエンドポイント定義
  services/
    youtube_service.py       YouTube動画検索、動画詳細、チャンネル情報取得
    comment_service.py       YouTubeコメント取得
    transcript_service.py    字幕取得
  analysis/
    feature_engineering.py   数値特徴量、バズスコア作成
    NLP_analyze.py           タイトル、タグのNLP特徴量作成
    comment_NLP_analyze.py   コメントの形態素解析、トレンド語抽出
    comment_sentiment_analyze.py コメント感情分析
    transcript_analyze.py    字幕のNLP特徴量作成
    data_regression.py       機械学習、SHAP分析
    data_processing.py       分析結果表示用データ作成
  db/
    database.py              SQLite接続
    data_repository.py       DB保存、DB取得処理
    SQL_statement.py         分析用SQL
    SQL_NLP_statement.py     NLP処理用SQL
  data/
    youtube.db               SQLite DB
    *.csv, *.xlsx, *.png     中間出力、分析出力
```

## 3. 処理フロー

### 3.1 データ収集 `collect()`

[main_process.py](main_process.py) の `collect()` が収集処理の中心です。

処理順序は以下です。

1. [config.py](config.py) の `create_config()` で検索条件を作成
2. [youtube_service.py](services/youtube_service.py) でYouTube動画を検索
3. 取得した動画IDから動画詳細情報を取得
4. チャンネル登録者数を取得
5. [comment_service.py](services/comment_service.py) で各動画のコメントを取得
6. [feature_engineering.py](analysis/feature_engineering.py) で数値特徴量と `buzz_score` を作成
7. [transcript_service.py](services/transcript_service.py) で字幕データを取得
8. [NLP_analyze.py](analysis/NLP_analyze.py) でタイトル、タグの特徴量を作成
9. [comment_NLP_analyze.py](analysis/comment_NLP_analyze.py) でコメントのトレンド語を抽出
10. [data_repository.py](db/data_repository.py) でSQLite DBへ保存

### 3.2 NLP後処理 `NLP_processing()`

SQLiteに保存済みのコメント、字幕データを再取得し、以下を実行します。

- コメント感情分析
- コメント内の強い言葉のスコア化
- 字幕の感情、構成、密度などの特徴量抽出
- 処理済みテーブルへの保存

### 3.3 分析処理 `analyze()`

保存済みデータを使い、以下を実行します。

- 回帰分析用データの前処理
- RandomForestによる再生数予測
- SHAPによる特徴量重要度の算出
- 高再生動画、低再生動画の字幕構成比較
- Flask画面表示用のデータ作成

## 4. YouTube API利用仕様

### 4.1 利用API

- `search.list`
  - 検索ワードに一致する動画IDを取得
  - 現在は1検索ワードにつき1ページ、最大50件取得
- `videos.list`
  - 動画の `snippet` と `statistics` を取得
  - 50動画IDごとにまとめて取得
- `channels.list`
  - チャンネル登録者数を取得
  - 50チャンネルIDごとにまとめて取得
- `commentThreads.list`
  - 各動画のトップレベルコメントを最大30件取得

### 4.2 クォータ上の注意

`search.list` はYouTube Data APIの中でもクォータ消費が大きい処理です。

現在の [config.py](config.py) では、`genres` と `contexts` の組み合わせから検索ワードを作成しています。検索ワード数が多いほど、`search.list` の実行回数が増えます。

また、コメント取得は動画IDごとに `commentThreads.list` を呼び出すため、検索結果の動画数が多いほどAPI呼び出し回数が増えます。

安全運用する場合は、以下のような制限を入れることが望ましいです。

- 1回の収集で使う検索ワード数を制限する
- コメント取得対象の動画数に上限を設ける
- GitHub Actions等の定期実行では、1日あたりの実行回数を制限する

## 5. 字幕取得仕様

[transcript_service.py](services/transcript_service.py) では `youtube_transcript_api` を使用しています。

この処理はYouTube Data APIキーを使用しないため、YouTube Data APIのクォータは基本的に消費しません。ただし、大量アクセス時にはIP制限や一時的な取得失敗が発生する可能性があります。

現在の主な仕様は以下です。

- 対象言語は `ja`, `en`
- 取得失敗時は最大5回リトライ
- 各リクエスト間に0から2秒のランダム待機
- `TranscriptsDisabled`, `NoTranscriptFound`, `VideoUnavailable` はスキップ
- `proxy_username`, `proxy_password` が設定されている場合はWebshareプロキシを使用

## 6. 保存データ

主な保存先はSQLite DBです。

```text
backend/data/youtube.db
```

主なテーブルは以下です。

- `youtube_data`
  - 動画ID、タイトル、再生数、いいね数、コメント数、チャンネルID、タグ、特徴量など
- `comment_raw_data`
  - 取得直後のコメントデータ
- `transcript_raw_data`
  - 取得直後の字幕データ
- `trend_word_data`
  - タイトルから抽出したトレンド語
- `trend_tag_data`
  - タグから抽出したトレンド語
- `trend_comment_data`
  - コメントから抽出したトレンド語
- `comment_data`
  - NLP処理後のコメント特徴量
- `transcript_data`
  - NLP処理後の字幕特徴量

また、処理途中で以下のようなCSV、Excel、画像ファイルも出力されます。

- `backend/data/processed.xlsx`
- `backend/data/NLP.xlsx`
- `backend/data/tags_NLP.xlsx`
- `backend/data/comment_processed.csv`
- `backend/data/comment_df_processed.xlsx`
- `backend/data/transcript.csv`
- `backend/data/transcript_features.csv`
- `backend/data/randomforest_shap_importance.csv`
- `backend/data/randomforest_shap_summary.png`

## 7. 起動方法

### 7.1 Flaskアプリを起動する場合

```powershell
cd "C:\Python Projects\youtube_buzz_analyzer_v2"
conda activate youtube_buzz_analyzer
python backend\main.py
```

起動後、ブラウザからFlask画面にアクセスします。

### 7.2 Pythonから収集処理を実行する場合

`main_process.py` には `collect()` が定義されていますが、ファイルを直接実行しても自動では呼び出されません。Python上から以下のように呼び出します。

```powershell
cd "C:\Python Projects\youtube_buzz_analyzer_v2\backend"
python -c "import main_process; main_process.collect()"
```

## 8. 環境変数

[config.py](config.py) は `backend/.env` を読み込みます。

必要な環境変数は以下です。

```text
YOUTUBE_API_KEY=YouTube Data APIキー
proxy_username=Webshareプロキシのユーザー名 任意
proxy_password=Webshareプロキシのパスワード 任意
PART=id,snippet 任意
TYPE=video 任意
RELEVANCELANGUAGE=ja 任意
VIDEOCATEGORYID=10 任意
```

GitHub Actionsで実行する場合、`.env` は使用せず、GitHub Secretsに `YOUTUBE_API_KEY` などを登録してworkflowから環境変数として渡す想定です。

## 9. 主な依存ライブラリ

このプログラムでは、主に以下の外部ライブラリを使用しています。

- Flask
- pandas
- numpy
- requests
- python-dotenv
- google-api-python-client
- youtube-transcript-api
- MeCab
- ipadic
- JaStopwordFilter
- pycld2
- asari
- nltk
- spacy
- scikit-learn
- lightgbm
- shap
- matplotlib
- openpyxl

現状、リポジトリ内に `requirements.txt` や `environment.yml` は確認できていません。別環境やGitHub Actionsで再現する場合は、依存ライブラリ定義ファイルを作成する必要があります。



## 10. 今後の改善候補

- `requirements.txt` または `environment.yml` の作成
- import形式を `backend.xxx` に統一
- GitHub Actions用workflowの作成
- APIクォータを考慮した検索ワード数、コメント取得数の上限設定
- 文字化けしている日本語文字列の修正
- 空データ時の例外処理追加
- DBスキーマ定義書の追加
- ログ出力の整理
- 収集処理、NLP処理、分析処理をCLIコマンドとして分離

## 11. 出力画面で表示される特徴量の説明

Flask画面の分析結果では、主に以下のグラフを表示します。

- SHAP特徴量重要度グラフ
  - RandomForestモデルが再生数を予測する際に、どの特徴量を重視したかを示します。
  - 値が大きいほど、再生数予測への影響が大きい特徴量です。
- 特徴量別散布図
  - 横軸に選択した特徴量、縦軸に再生数を置き、特徴量と再生数の関係を確認します。
- 高再生動画、低再生動画の字幕タイムライン比較
  - 動画全体を8区間に分け、どの区間に字幕量が多いかを比較します。
  - 高再生動画と低再生動画で、構成上の違いがあるかを見るためのグラフです。

### 11.1 基本指標

| 表示名 | 意味 |
| --- | --- |
| 高評価数 | 動画についた高評価数です。動画への反応の強さを表します。 |
| コメント数 | 動画についたコメント数です。視聴者の参加度や話題性を表します。 |
| 登録者数 | 投稿チャンネルの登録者数です。チャンネル自体の規模を表します。 |
| 再生数あたりの高評価率 | 再生数に対して高評価がどれくらい多いかを表します。単純な高評価数よりも、視聴者の満足度に近い指標です。 |
| 再生数あたりのコメント数 | 再生数に対してコメントがどれくらい多いかを表します。動画が議論や反応を生んでいるかを見る指標です。 |

### 11.2 タイトル由来の特徴量

| 表示名 | 意味 |
| --- | --- |
| タイトル長 | タイトルの文字数です。短いタイトル、長いタイトルのどちらが再生数に関係するかを見るための特徴量です。 |
| 興味を引く単語数(タイトル) | 「なぜ」「実は」など、視聴者の興味を引く単語がタイトルに含まれる度合いです。 |
| ハウツー系単語数(タイトル) | 「方法」「解説」「初心者」など、役に立つ情報を示す単語の度合いです。 |
| 感情単語数(タイトル) | 「最高」「泣ける」など、感情を動かす単語の度合いです。 |
| ネガティブ単語数(タイトル) | 「失敗」「危険」など、ネガティブな印象を持つ単語の度合いです。 |
| 強調単語数(タイトル) | 「絶対」「本気」など、タイトル内で強く訴求する単語の度合いです。 |
| ？が含まれているか(タイトル) | タイトルに疑問符が含まれるかを表します。疑問形タイトルの効果を見るための特徴量です。 |
| ！が含まれているか(タイトル) | タイトルに感嘆符が含まれる数です。強調表現の多さを表します。 |
| 数字が含まれているか(タイトル) | タイトルに数字が含まれるかを表します。ランキング、期間、回数などの訴求を見るための特徴量です。 |
| カバー動画かどうか(タイトル) | タイトルからカバー、歌ってみた、弾いてみた等の動画かどうかを判定した特徴量です。 |
| トレンドワードの影響度(タイトル) | 収集した動画群の中でよく出る単語が、その動画タイトルにどれくらい含まれるかを表します。 |

### 11.3 タグ由来の特徴量

| 表示名 | 意味 |
| --- | --- |
| 動画タグ数 | YouTube動画に設定されているタグの数です。投稿者が検索流入をどれくらい意識しているかの参考になります。 |
| トレンドワードの影響度(タグ) | 収集した動画群の中でよく出るタグが、その動画にどれくらい含まれるかを表します。 |

### 11.4 コメント由来の特徴量

| 表示名 | 意味 |
| --- | --- |
| ポジティブ度(コメント) | コメントの感情分析により、肯定的な反応がどれくらい多いかを表します。 |
| ネガティブ度(コメント) | コメントの感情分析により、否定的な反応がどれくらい多いかを表します。 |
| 賞賛単語数(コメント) | 「すごい」「最高」など、賞賛を示す単語の出現度合いです。 |
| 感情単語数(コメント) | 感動、嬉しさ、泣けるなど、感情の強い反応を示す単語の出現度合いです。 |
| 驚き単語数(コメント) | 驚きや意外性を示す単語の出現度合いです。 |
| 中毒単語数(コメント) | 「何回も聴く」「リピート」など、繰り返し視聴につながりそうな単語の出現度合いです。 |
| 共感単語数(コメント) | 「わかる」「共感」など、視聴者同士の共感を示す単語の出現度合いです。 |
| 音楽オタク単語数(コメント) | 音作り、歌唱、演奏、アレンジなど、音楽的な細部に反応している単語の出現度合いです。 |
| バズ単語数(コメント) | 「伸びる」「流行る」など、動画の拡散や人気化に関する単語の出現度合いです。 |
| ネガティブ単語数(コメント) | 否定的な反応や不満を表す単語の出現度合いです。 |
| ファン単語数(コメント) | 推し、ファン、応援など、コミュニティ性を示す単語の出現度合いです。 |
| バズ単語数合計(コメント) | コメント内の強い反応を示す単語スコアを合計した指標です。 |

### 11.5 字幕由来の特徴量

| 表示名 | 意味 |
| --- | --- |
| 内容が濃い動画箇所 | 10秒ごとに区切った字幕の中で、最も文字量が多い区間の値です。情報量が集中している箇所を表します。 |
| 動画内容の濃さの分散 | 字幕量が動画全体で均等か、一部に集中しているかを表します。 |
| ポジティブな単語が最も多い動画箇所 | 字幕内でポジティブ感情が最も強く出た区間の値です。 |
| ネガティブな単語が最も多い動画箇所 | 字幕内でネガティブ感情が最も強く出た区間の値です。 |
| ポジティブワードの件数 | 字幕内に出てくるポジティブな単語のスコア合計です。 |
| ネガティブワードの件数 | 字幕内に出てくるネガティブな単語のスコア合計です。 |
| 驚き単語数(字幕) | 字幕内に出てくる驚きに関する単語のスコア合計です。 |
| 音楽単語数(字幕) | 字幕内に出てくる音楽関連単語のスコア合計です。 |
| ストーリー単語数(字幕) | 字幕内に出てくる物語性、展開、感動に関する単語のスコア合計です。 |
| フック部(動画時間30秒まで)の単語数 | 動画開始から30秒までの字幕量です。冒頭でどれくらい情報や印象を出しているかを見る指標です。 |
| 秒ごとの単語数 | 動画全体に対する字幕量の密度です。テンポや情報量の多さを表します。 |
| 場面ごとの感情の起伏 | ポジティブ感情とネガティブ感情の差です。動画内で感情の変化が大きいかを見る指標です。 |
| バズ単語数合計(字幕) | 字幕内の感情、驚き、音楽、ストーリー系単語スコアを合計した指標です。 |

### 11.6 タイムライン比較グラフ

高再生動画と低再生動画の字幕を、それぞれ動画時間に沿って8区間に分けます。

| 表示項目 | 意味 |
| --- | --- |
| section | 動画を時間順に8分割した区間です。1が冒頭、8が終盤を表します。 |
| wordCountRate | その区間に字幕量がどれくらい集中しているかを表します。各動画内の字幕総量に対する割合です。 |

このグラフでは、例えば以下のような観点で説明できます。

- 高再生動画は冒頭に情報量が集中しているか
- サビや見せ場にあたる中盤、終盤で字幕量が増えているか
- 低再生動画と比べて、構成上のメリハリがあるか

### 11.7 説明時の注意

これらの特徴量は、再生数との関係を調べるための分析用指標です。SHAPで重要度が高く出た特徴量でも、それが直接バズの原因であるとは限りません。

そのため、発表時は「この特徴量が高いから必ず再生される」という説明ではなく、「このデータセットでは、再生数を予測するうえでこの特徴量が重要視された」という説明にするのが適切です。
