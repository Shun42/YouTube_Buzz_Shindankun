
// グラフを保持する変数
let word_cloud_comment;
let word_cloud_tags;
let word_cloud_title;
const wordCloudColors = [
    "#1b9e77",
    "#d95f02",
    "#7570b3",
    "#e7298a",
    "#66a61e",
    "#e6ab02",
    "#a6761d",
    "#1f78b4",
    "#b2df8a",
    "#fb9a99",
    "#fdbf6f",
    "#cab2d6"
];
function createWordCloudSizes(items, minSize = 12, maxSize = 42) {
    const counts = items.map(item => Number(item.count) || 0);
    if (counts.length === 0) {
        return [];
    }

    const minCount = Math.min(...counts);
    const maxCount = Math.max(...counts);
    if (minCount === maxCount) {
        return counts.map(() => Math.round((minSize + maxSize) / 2));
    }

    const minRoot = Math.sqrt(minCount);
    const maxRoot = Math.sqrt(maxCount);
    return counts.map(count => {
        const normalized = (Math.sqrt(count) - minRoot) / (maxRoot - minRoot);
        return Math.round(minSize + normalized * (maxSize - minSize));
    });
}
// グラフを作る関数
export async function createwordcloudChart() {
    // Flask APIへアクセス
    const response_comment = await fetch("/api/wordcloud/comment/");
    // JSONへ変換
    const comment_data = await response_comment.json();
    const response_tag = await fetch("/api/wordcloud/tag/");
    const tag_data = await response_tag.json();
    const response_word = await fetch("/api/wordcloud/word/");
    const word_data = await response_word.json();
    const word_comment = comment_data.map(item => item.word)
    const count_comment = createWordCloudSizes(comment_data, 12, 40)
    const word_tag = tag_data.map(item => item.word)
    const count_tag = createWordCloudSizes(tag_data, 12, 44)
    const word_word = word_data.map(item => item.word)
    const count_word = createWordCloudSizes(word_data, 12, 44)
    // canvas取得
    const ctx_six = document.getElementById("wordCloud_comment");
    const ctx_seven = document.getElementById("wordCloud_tag");
    const ctx_eight = document.getElementById("wordCloud_word");
    // 既存グラフがあるなら削除
    // Chart.js生成
    word_cloud_comment = new Chart(ctx_six, {

        type: "wordCloud",
        data: {
            labels: word_comment,
            datasets: [
                {
                    label: "ワードクラウド(コメント頻出語)",
                    data: count_comment,
        }
    ]},
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: {
                word: {
                    padding: 2,
                    color: function(context) {
                        return wordCloudColors[context.index % wordCloudColors.length];
                    }
                }
            }
        }
    });
// Chart.js生成
    word_cloud_tags = new Chart(ctx_seven, {

        type: "wordCloud",
        data: {
            labels: word_tag,
            datasets: [
                {
                    label: "ワードクラウド(タグ頻出語)",
                    data: count_tag,
        }
    ]},
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: {
                word: {
                    padding: 2,
                    color: function(context) {
                        return wordCloudColors[context.index % wordCloudColors.length];
                    }
                }
            }
        }
    });
    word_cloud_title = new Chart(ctx_eight, {

        type: "wordCloud",
        data: {
            labels: word_word,
            datasets: [
                {
                    label: "ワードクラウド(タイトル頻出語)",
                    data: count_word,
        }
    ]},
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: {
                word: {
                    padding: 2,
                    color: function(context) {
                        return wordCloudColors[context.index % wordCloudColors.length];
                    }
                }
            }
        }
    });
}            
