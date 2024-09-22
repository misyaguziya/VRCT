export const translator_status = [
    { translator_id: "DeepL", translator_name: "DeepL", is_available: false },
    { translator_id: "DeepL_API", translator_name: `DeepL\nAPI`, is_available: false },
    { translator_id: "Google", translator_name: "Google", is_available: false },
    { translator_id: "Bing", translator_name: "Bing", is_available: false },
    { translator_id: "Papago", translator_name: "Papago", is_available: false },
    { translator_id: "CTranslate2", translator_name: `Internal\n(Default)`, is_available: false },
];


export const generateTestData = (num) => {
    const testDataArray = [];
    const messagesJa = [
        "今日はとてもいい天気ですね。",
        "次の会議は何時に始まりますか？",
        "新しいプロジェクトについて話しましょう。",
        "お疲れ様です。今日は早く帰れますか？",
        "この書類にサインをお願いします。",
        "次の休暇はどこに行きますか？",
        "先週のレポートを見ましたか？",
        "この問題をどうやって解決しますか？",
        "週末は何をする予定ですか？",
        "新しいアイデアを聞かせてください。",
        "こんにちは、調子はどうですか？",
        "おはようございます、今日の予定は何ですか？",
        "こんばんは、今日は楽しかったですか？",
        "ありがとう、助かりました。",
        "さようなら、また会いましょう。",
        "はい、分かりました。",
        "いいえ、ちょっと難しいです。",
        "すみません、もう一度言ってください。",
        "お願いします、手伝ってください。",
        "お疲れ様です、今日も頑張りましょう。",
    ];
    const messagesEn = [
        "The weather is very nice today.",
        "What time does the next meeting start?",
        "Let's talk about the new project.",
        "Good job today. Can you leave early today?",
        "Please sign this document.",
        "Where are you going for the next vacation?",
        "Did you see last week's report?",
        "How do we solve this problem?",
        "What are your plans for the weekend?",
        "Tell me about your new idea.",
        "Hello, how are you?",
        "Good morning, what are your plans for today?",
        "Good evening, did you have a good day?",
        "Thank you, that was helpful.",
        "Goodbye, see you again.",
        "Yes, understood.",
        "No, it's a bit difficult.",
        "Sorry, could you say that again?",
        "Please, help me out.",
        "Good job today, let's do our best again tomorrow.",
    ];
    const statuses = ["sent", "received"];

    for (let i = 0; i < num; i++) {
        const uuid = crypto.randomUUID();
        const date = new Date().toLocaleTimeString(
            "ja-JP",
            { hour12: false, hour: "2-digit", minute: "2-digit" }
        );
        const messageIndex = Math.floor(Math.random() * messagesJa.length);
        const status = statuses[Math.floor(Math.random() * statuses.length)];

        const testData = {
            id: uuid,
            category: status,
            status: status,
            created_at: date,
            messages: {
                original: messagesJa[messageIndex],
                translated: [
                    messagesEn[messageIndex],
                ],
            },
        };
        testDataArray.push(testData);
    }

    return testDataArray;
};

export const word_filter_list = [
    { value: "りんご", is_redoable: false },
    { value: "forest", is_redoable: false },
    { value: "もり", is_redoable: false },
    { value: "elephant", is_redoable: false },
    { value: "penguin", is_redoable: false },
    { value: "やま", is_redoable: false },
    { value: "notebook", is_redoable: false },
    { value: "zebra", is_redoable: false },
    { value: "ちょう", is_redoable: false },
    { value: "dinosaur", is_redoable: false },
    { value: "たいこ", is_redoable: false },
    { value: "カンガルー", is_redoable: false },
    { value: "ふうせん", is_redoable: false },
    { value: "candle", is_redoable: false },
    { value: "tiger", is_redoable: false },
    { value: "umbrella", is_redoable: false },
    { value: "garden", is_redoable: false },
    { value: "ペンギン", is_redoable: false },
    { value: "ひまわり", is_redoable: false },
    { value: "kangaroo", is_redoable: false },
    { value: "とうだい", is_redoable: false },
    { value: "シロフォン", is_redoable: false },
    { value: "ひこうき", is_redoable: false },
    { value: "しろ", is_redoable: false },
    { value: "しあわせ", is_redoable: false },
    { value: "xylophone", is_redoable: false },
    { value: "volcano", is_redoable: false },
    { value: "drum", is_redoable: false },
    { value: "lighthouse", is_redoable: false },
    { value: "quicksand", is_redoable: false },
    { value: "airplane", is_redoable: false },
    { value: "しまうま", is_redoable: false },
    { value: "sunflower", is_redoable: false },
    { value: "ジャングル", is_redoable: false },
    { value: "くじら", is_redoable: false },
    { value: "apple", is_redoable: false },
    { value: "island", is_redoable: false },
    { value: "ocean", is_redoable: false },
    { value: "rainbow", is_redoable: false },
    { value: "castle", is_redoable: false },
    { value: "かさ", is_redoable: false },
    { value: "ぞう", is_redoable: false },
    { value: "balloon", is_redoable: false },
    { value: "happiness", is_redoable: false },
    { value: "whale", is_redoable: false },
    { value: "にじ", is_redoable: false },
    { value: "ヨット", is_redoable: false },
    { value: "しま", is_redoable: false },
    { value: "かざん", is_redoable: false },
    { value: "ノート", is_redoable: false },
    { value: "mountain", is_redoable: false },
    { value: "うみ", is_redoable: false },
    { value: "ジャングル", is_redoable: false },
];