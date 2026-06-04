
export async function createStrongWordsScatter() {
    const response = await fetch("/api/strong_words_scatter/");
    const result = await response.json();

    const rawData = result.data;
    const transcriptThreshold = result.thresholds.transcript;
    const commentsThreshold = result.thresholds.comments;

    const buzzTypeColors = {
        "本物バズ": "rgba(255, 99, 132, 0.8)",
        "釣り・内容先行型": "rgba(255, 159, 64, 0.8)",
        "共感型": "rgba(54, 162, 235, 0.8)",
        "低反応型": "rgba(150, 150, 150, 0.6)"
    };

    const groupedData = {
        "本物バズ": [],
        "釣り・内容先行型": [],
        "共感型": [],
        "低反応型": []
    };

    rawData.forEach(item => {
        groupedData[item.buzz_type].push(item);
    });

    const datasets = Object.keys(groupedData).map(type => {
        return {
            label: type,
            data: groupedData[type],
            backgroundColor: buzzTypeColors[type],
            pointRadius: 6,
            pointHoverRadius: 9
        };
    });

    const ctx = document.getElementById("strongWordsScatter");

    new Chart(ctx, {
        type: "scatter",
        data: {
            datasets: datasets
        },
        options: {
            responsive: true,
            parsing: {
                xAxisKey: "x",
                yAxisKey: "y"
            },
            scales: {
                x: {
                    type: "linear",
                    title: {
                        display: true,
                        text: "Transcript strong_words_score",
                        font: {
                            size: 18,
                            weight: 'bold'
                        }
                    }

                },
                y: {
                    type: "linear",
                    title: {
                        display: true,
                        text: "Comments strong_words_score",
                            font: {
                            size: 18,
                            weight: 'bold'
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const item = context.raw;

                            return [
                                `Transcript強さ: ${item.x}`,
                                `Comments強さ: ${item.y}`
                            ];
                        }
                    }
                },
                annotation: {
                    annotations: {
                        transcriptLine: {
                            type: "line",
                            xMin: transcriptThreshold,
                            xMax: transcriptThreshold,
                            borderWidth: 2,
                            borderDash: [6, 6],
                            label: {
                                display: true,
                                content: "Transcriptしきい値",
                                position: "start"
                            }
                        },
                        commentsLine: {
                            type: "line",
                            yMin: commentsThreshold,
                            yMax: commentsThreshold,
                            borderWidth: 2,
                            borderDash: [6, 6],
                            label: {
                                display: true,
                                content: "Commentsしきい値",
                                position: "start"
                            }
                        }
                    }
                }
            }
        }
    });
}
