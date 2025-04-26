
/**
 * SRT形式の文字列を解析する関数
 * 改行コードを正規化し、空行で分割して解析する
 * （actor は存在しないため、空文字列をセット）
 */
export const parseSRT = (data) => {
    const cues = [];
    const normalizedData = data.replace(/\r\n/g, "\n").trim();
    const blocks = normalizedData.split(/\n\s*\n/);
    blocks.forEach((block) => {
        const lines = block.split("\n").filter((line) => line.trim() !== "");
        if (lines.length >= 3) {
            const index = parseInt(lines[0], 10);
            const timeMatch = lines[1].match(/([\d:,]+)\s+-->\s+([\d:,]+)/);
            if (!timeMatch) return;
            const start = parseTime(timeMatch[1]);
            const end = parseTime(timeMatch[2]);
            const text = lines.slice(2).join("\n");
            cues.push({ index, startTime: start, endTime: end, actor: "", text });
        }
    });
    return cues;
};

/**
 * ASS形式の文字列を解析する関数
 * [Events] セクション内の "Dialogue:" 行から、
 * フォーマット "Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
 * に沿って分割する。
 * ここでは Name を actor、Text を text として抽出する。
 */
export const parseASS = (data) => {
    const cues = [];
    const lines = data.split(/\r?\n/);
    let index = 1;
    lines.forEach((line) => {
        if (line.startsWith("Dialogue:")) {
            const dialogueLine = line.substring("Dialogue:".length).trim();
            const parts = dialogueLine.split(",");
            // parts[0]: Layer, parts[1]: Start, parts[2]: End, parts[3]: Style, parts[4]: Name, parts[5]: MarginL, parts[6]: MarginR, parts[7]: MarginV, parts[8]: Effect, parts[9]～: Text
            if (parts.length < 10) return;
            const startTime = parseASSTime(parts[1].trim());
            const endTime = parseASSTime(parts[2].trim());
            const actor = parts[4].trim();
            const text = parts.slice(9).join(",").trim();
            cues.push({ index: index++, startTime, endTime, actor, text });
        }
    });
    return cues;
};

/**
 * "H:MM:SS.cc" 形式の ASS 時刻文字列を秒数に変換する関数
 * 例: "0:00:10.52" → 10.52 秒
 */
export const parseASSTime = (timeString) => {
    const parts = timeString.split(":");
    if (parts.length !== 3) return 0;
    const hours = parseFloat(parts[0]);
    const minutes = parseFloat(parts[1]);
    const seconds = parseFloat(parts[2]);
    return hours * 3600 + minutes * 60 + seconds;
};

/**
 * "HH:MM:SS,mmm" 形式の SRT 時刻文字列を秒数に変換する関数
 */
export const parseTime = (timeString) => {
    const [hms, ms] = timeString.split(",");
    const [hours, minutes, seconds] = hms.split(":").map(Number);
    return hours * 3600 + minutes * 60 + seconds + Number(ms) / 1000;
};

const padTime = (int) => {
    return String(int).padStart(2, "0");
};

export const secToDayTime = (seconds) => {
    const day = Math.floor(seconds / 86400);
    const hour = Math.floor((seconds % 86400) / 3600);
    const min = Math.floor((seconds % 3600) / 60);
    const sec = seconds % 60;
    let time = "";
    // day が 0 の場合は「日」は出力しない（hour や min も同様）
    if (day !== 0) {
        time = `${day}日${hour}時間${min}分${sec}秒`;
    } else if (hour !== 0) {
        time = `${padTime(hour)}:${padTime(min)}:${padTime(sec)}`;
    } else {
        time = `${padTime(min)}:${padTime(sec)}`;
    }
    // } else {
    //     time = `${padTime(sec)}`;
    // }
    return time;
};


// HH:MM:SS 形式に変換する補助関数
export const formatTime = (timeInSeconds) => {
    const hours = Math.floor(timeInSeconds / 3600);
    const minutes = Math.floor((timeInSeconds % 3600) / 60);
    const seconds = Math.floor(timeInSeconds % 60);
    return (
        String(hours).padStart(2, "0") +
        ":" +
        String(minutes).padStart(2, "0") +
        ":" +
        String(seconds).padStart(2, "0")
    );
};
