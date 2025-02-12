import React, { useState, useRef, useEffect } from "react";
import styles from "./PluginsSection.module.scss";
import { useSendTextToOverlay } from "@logics_configs";

export const PluginsSection = () => {
    const { sendTextToOverlay } = useSendTextToOverlay();
    const [srtContent, setSrtContent] = useState("");
    const [cues, setCues] = useState([]);
    const [isPlaying, setIsPlaying] = useState(false);

    // 再生モード ("relative": ボタン押下から、"absolute": 指定時刻から)
    const [playbackMode, setPlaybackMode] = useState("relative");
    // 絶対モード用の再生開始時刻（ドロップダウンで選択、HH:MM）
    const [targetHour, setTargetHour] = useState("19");
    const [targetMinute, setTargetMinute] = useState("00");

    // カウントダウンの状態
    // initialCountdown: 開始ボタン押下時に計算される元の残り秒数
    const [initialCountdown, setInitialCountdown] = useState(null);
    // countdownAdjustment: ユーザーが上下ボタンで調整する値（秒単位）
    const [countdownAdjustment, setCountdownAdjustment] = useState(0);
    // effectiveCountdown: (initialCountdown + countdownAdjustment) から経過秒数を差し引いた表示用の値
    const [effectiveCountdown, setEffectiveCountdown] = useState(null);
    // cuesScheduled: 字幕タイマーが一度スケジュールされたか
    const [cuesScheduled, setCuesScheduled] = useState(false);

    // setTimeout/setInterval のタイマーID管理用
    const timersRef = useRef([]);
    // ファイル入力リセット用の ref
    const fileInputRef = useRef(null);

    // ファイルアップロード処理
    const handleFileUpload = (event) => {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            setSrtContent(content);
            const parsedCues = parseSRT(content);
            setCues(parsedCues);
            console.log("パース結果:", parsedCues);
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        };
        reader.readAsText(file);
    };

    // 字幕開始時の処理
    const startFunction = (cue) => {
        console.log(`字幕開始 (index: ${cue.index}): ${cue.text}`);
        sendTextToOverlay(cue.text);
    };

    // 字幕終了時の処理
    const endFunction = (cue) => {
        console.log(`字幕終了 (index: ${cue.index}): ${cue.text}`);
        // 必要に応じて終了処理（例：テキストクリア）
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

    // cues のスケジュールを行う（offset は countdownAdjustment * 1000）
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
        // 初期表示は (initialValue + countdownAdjustment)
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
            scheduleCues(0);
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
                    SRTファイルを選択:
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".srt"
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
                        <label className={styles.label}>
                            再生開始時刻 (HH:MM):
                        </label>
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
            <div className={styles.countdown}>
                <span>カウントダウン: {effectiveCountdown} 秒</span>
                <button
                    onClick={() => setEffectiveCountdown((prev) => prev + 1)}
                    className={styles.adjustButton}
                >
                    ▲
                </button>
                <button
                    onClick={() => setEffectiveCountdown((prev) => prev - 1)}
                    className={styles.adjustButton}
                >
                    ▼
                </button>
            </div>
            {cues.length > 0 && (
                <div className={styles.subtitleSection}>
                    <h2>字幕一覧</h2>
                    <table className={styles.table}>
                        <thead>
                            <tr>
                                <th>番号</th>
                                <th>開始</th>
                                <th>終了</th>
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
 * ユーザー提示のサンプルに基づき、改行コードを正規化後、空行で分割して解析
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
            cues.push({ index, startTime: start, endTime: end, text });
        }
    });
    return cues;
};

/**
 * "HH:MM:SS,mmm" 形式の文字列を秒数に変換する関数
 */
const parseTime = (timeString) => {
    const [hms, ms] = timeString.split(",");
    const [hours, minutes, seconds] = hms.split(":").map(Number);
    return hours * 3600 + minutes * 60 + seconds + Number(ms) / 1000;
};
