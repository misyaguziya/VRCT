import React, { useState, useRef, useEffect } from "react";
import styles from "./SubtitleSystemContainer.module.scss";
import { useSendTextToOverlay } from "@logics_configs";

export const SubtitleSystemContainer = () => {
    const { sendTextToOverlay } = useSendTextToOverlay();
    const [srtContent, setSrtContent] = useState("");
    const [cues, setCues] = useState([]);
    const [isPlaying, setIsPlaying] = useState(false);

    // 再生モード ("relative": ボタン押下から、"absolute": 指定時刻から)
    const [playbackMode, setPlaybackMode] = useState("relative");
    // 絶対モード用の再生開始時刻（ドロップダウンで選択、HH:MM）
    const [targetHour, setTargetHour] = useState("19");
    const [targetMinute, setTargetMinute] = useState("00");

    // カウントダウン状態
    // initialCountdown: 再生開始ボタン押下時に算出される元の残り秒数
    const [initialCountdown, setInitialCountdown] = useState(null);
    // countdownAdjustment: ユーザーが上下ボタンで調整する値（秒単位）
    const [countdownAdjustment, setCountdownAdjustment] = useState(0);
    // effectiveCountdown: (initialCountdown + countdownAdjustment) から経過秒数を差し引いた表示用の値
    const [effectiveCountdown, setEffectiveCountdown] = useState(null);
    // cuesScheduled: 字幕タイマーが一度スケジュールされたか
    const [cuesScheduled, setCuesScheduled] = useState(false);

    // タイマー（setTimeout/setInterval）のID管理用
    const timersRef = useRef([]);
    // ファイル入力リセット用の ref
    const fileInputRef = useRef(null);

    // ファイルアップロード時の処理
    const handleFileUpload = (event) => {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            setSrtContent(content);
            let parsedCues = [];
            // 拡張子により ASS と SRT を判定
            if (file.name.toLowerCase().endsWith(".ass")) {
                parsedCues = parseASS(content);
            } else {
                parsedCues = parseSRT(content);
            }
            setCues(parsedCues);
            console.log("Parsed cues:", parsedCues);
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        };
        reader.readAsText(file);
    };

    // 字幕開始時の処理
    const startFunction = (cue) => {
        let send_text = "";
        if (cue.actor !== "") {
            send_text = `[${cue.actor}] ${cue.text}`;
        } else {
            send_text = `${cue.text}`;
        }
        console.log(`字幕開始 (index: ${cue.index}) send_text:${send_text}`);
        sendTextToOverlay(send_text);
    };

    // 字幕終了時の処理
    const endFunction = (cue) => {
        console.log(`字幕終了 (index: ${cue.index}): ${cue.text}`);
        // 必要に応じた終了処理（例：テキストクリア）を実装可能
        // sendTextToOverlay("");
    };

    // すべてのタイマーを停止し、各状態を初期化する
    const handleStop = () => {
        timersRef.current.forEach((timerId) => {
            clearTimeout(timerId);
            clearInterval(timerId);
        });
        timersRef.current = [];
        console.log("再生を停止しました。");
        setIsPlaying(false);
        setInitialCountdown(null);
        setEffectiveCountdown(null);
        setCountdownAdjustment(0);
        setCuesScheduled(false);
    };

    // cues のスケジュールを行う（字幕開始時のオフセットは countdownAdjustment * 1000）
    const scheduleCues = (offset) => {
        cues.forEach((cue) => {
            const startDelay = cue.startTime * 1000 + offset;
            const endDelay = cue.endTime * 1000 + offset;
            if (startDelay >= 0) {
                const timerId = setTimeout(() => startFunction(cue), startDelay);
                timersRef.current.push(timerId);
            }
            if (endDelay >= 0) {
                const timerId = setTimeout(() => endFunction(cue), endDelay);
                timersRef.current.push(timerId);
            }
        });
    };

    // カウントダウンタイマーの開始
    const startCountdownInterval = (initialValue) => {
        setEffectiveCountdown(initialValue + countdownAdjustment);
        const countdownInterval = setInterval(() => {
            setEffectiveCountdown((prev) => {
                if (prev <= 1) {
                    clearInterval(countdownInterval);
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);
        timersRef.current.push(countdownInterval);
    };

    // 「再生開始」ボタン押下時の処理
    const handleStart = () => {
        handleStop();
        setIsPlaying(true);
        setCuesScheduled(false);

        let computedCountdown = 0;
        if (playbackMode === "absolute") {
            const now = new Date();
            const hour = parseInt(targetHour, 10);
            const minute = parseInt(targetMinute, 10);
            let targetDate = new Date(
                now.getFullYear(),
                now.getMonth(),
                now.getDate(),
                hour,
                minute,
                0,
                0
            );
            if (targetDate.getTime() < now.getTime()) {
                targetDate.setDate(targetDate.getDate() + 1);
            }
            computedCountdown = Math.ceil((targetDate.getTime() - now.getTime()) / 1000);
        } else {
            computedCountdown = 10; // relative モードの場合は固定値
        }
        setInitialCountdown(computedCountdown);
        setEffectiveCountdown(computedCountdown + countdownAdjustment);
        sendTextToOverlay((computedCountdown + countdownAdjustment).toString());
        startCountdownInterval(computedCountdown);
    };

    // effectiveCountdown が 0 になったとき、字幕開始
    useEffect(() => {
        if (
            isPlaying &&
            effectiveCountdown !== null &&
            effectiveCountdown <= 0 &&
            !cuesScheduled
        ) {
            sendTextToOverlay("Start.");
            console.log("Start.");
            // オフセットは countdownAdjustment × 1000 を字幕に反映
            scheduleCues(countdownAdjustment * 1000);
            setCuesScheduled(true);
        }
    }, [effectiveCountdown, isPlaying, cuesScheduled, countdownAdjustment]);

    // テーブル内の字幕行をクリック（relative モードのみ）でジャンプ
    const handleJump = (jumpCue) => {
        if (playbackMode !== "relative") return;
        handleStop();
        const offset = -jumpCue.startTime * 1000;
        scheduleCues(offset);
        setIsPlaying(true);
    };

    // HH:MM:SS 形式に変換する補助関数
    const formatTime = (timeInSeconds) => {
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

    // ファイルクリア
    const handleClearFile = () => {
        handleStop();
        setSrtContent("");
        setCues([]);
    };

    return (
        <div className={styles.container}>
            <h1>字幕プレイヤー</h1>
            <div className={styles.fileSection}>
                <label className={styles.label}>
                    SRT/ASSファイルを選択:
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".srt,.ass"
                        onChange={handleFileUpload}
                        className={styles.input}
                    />
                </label>
                <button onClick={handleClearFile} className={styles.fileClear}>
                    ファイルクリア
                </button>
            </div>
            <div className={styles.modeSection}>
                <label className={styles.label}>
                    再生モード:
                    <select
                        value={playbackMode}
                        onChange={(e) => setPlaybackMode(e.target.value)}
                        className={styles.select}
                    >
                        <option value="relative">相対（ボタン押下から）</option>
                        <option value="absolute">絶対（指定時刻から）</option>
                    </select>
                </label>
                {playbackMode === "absolute" && (
                    <div className={styles.timeSection}>
                        <label className={styles.label}>再生開始時刻 (HH:MM):</label>
                        <div className={styles.timeSelects}>
                            <select
                                value={targetHour}
                                onChange={(e) => setTargetHour(e.target.value)}
                                className={styles.select}
                            >
                                {Array.from({ length: 24 }, (_, i) => {
                                    const hour = i.toString().padStart(2, "0");
                                    return (
                                        <option key={i} value={hour}>
                                            {hour}
                                        </option>
                                    );
                                })}
                            </select>
                            <span>:</span>
                            <select
                                value={targetMinute}
                                onChange={(e) => setTargetMinute(e.target.value)}
                                className={styles.select}
                            >
                                {Array.from({ length: 60 }, (_, i) => {
                                    const minute = i.toString().padStart(2, "0");
                                    return (
                                        <option key={i} value={minute}>
                                            {minute}
                                        </option>
                                    );
                                })}
                            </select>
                        </div>
                    </div>
                )}
            </div>
            <div className={styles.controlSection}>
                <button
                    onClick={handleStart}
                    className={isPlaying ? styles.is_playing : styles.primary}
                >
                    {isPlaying ? "再生中" : "再生開始"}
                </button>
                <button onClick={handleStop} className={styles.secondary}>
                    停止
                </button>
            </div>
            {/* カウントダウン表示：字幕開始前は常に表示 */}
            {effectiveCountdown !== null && !cuesScheduled && (
                <div className={styles.countdown}>
                    <span>カウントダウン: {effectiveCountdown} 秒</span>
                    <button
                        onClick={() =>
                            setEffectiveCountdown((prev) => prev + 1)
                        }
                        className={styles.adjustButton}
                    >
                        ▲
                    </button>
                    <button
                        onClick={() =>
                            setEffectiveCountdown((prev) => prev - 1)
                        }
                        className={styles.adjustButton}
                    >
                        ▼
                    </button>
                </div>
            )}
            {/* 字幕一覧の表示（relative モードの場合、クリックでジャンプ） */}
            {cues.length > 0 && (
                <div className={styles.subtitleSection}>
                    <h2>字幕一覧</h2>
                    <table className={styles.table}>
                        <thead>
                            <tr>
                                <th>番号</th>
                                <th>開始</th>
                                <th>終了</th>
                                <th>Actor</th>
                                <th>テキスト</th>
                            </tr>
                        </thead>
                        <tbody className={styles.subtitle_lists}>
                            {cues.map((cue) => (
                                <tr
                                    key={cue.index}
                                    onClick={() => handleJump(cue)}
                                    className={styles.tableRow}
                                >
                                    <td>{cue.index}</td>
                                    <td>{formatTime(cue.startTime)}</td>
                                    <td>{formatTime(cue.endTime)}</td>
                                    <td>{cue.actor}</td>
                                    <td>{cue.text}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <p className={styles.note}>
                        ※ 行をクリックすると、その字幕の位置にジャンプします。（相対モードのみ）
                    </p>
                </div>
            )}
        </div>
    );
};

/**
 * SRT形式の文字列を解析する関数
 * 改行コードを正規化し、空行で分割して解析する
 * （actor は存在しないため、空文字列をセット）
 */
const parseSRT = (data) => {
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
const parseASS = (data) => {
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
const parseASSTime = (timeString) => {
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
const parseTime = (timeString) => {
    const [hms, ms] = timeString.split(",");
    const [hours, minutes, seconds] = hms.split(":").map(Number);
    return hours * 3600 + minutes * 60 + seconds + Number(ms) / 1000;
};
