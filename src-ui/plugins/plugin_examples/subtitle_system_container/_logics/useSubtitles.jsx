import { useStore, useStoreContext } from "../../store/store.js";

// import { useSendTextToOverlay } from "@logics_configs";
// import {
//     useStore_SubtitleFileName,
//     useStore_IsSubtitlePlaying,
//     useStore_SubtitlePlaybackMode,
//     useStore_SubtitleAbsoluteTargetTime,
//     useStore_IsCuesScheduled,
//     useStore_CountdownAdjustment,
//     useStore_EffectiveCountdown,
//     useStore_SubtitleCues,

//     useStore_SubtitleTimers,
//     useStore_SubtitleCountdownTimerId,
// } from "../../store/store.js";

export const useSubtitles = () => {
    const logic_configs = useStoreContext();
    const { sendTextToOverlay } = logic_configs.useSendTextToOverlay();

    const { currentSubtitleFileName, updateSubtitleFileName } = useStore("useStore_SubtitleFileName");
    const { currentIsSubtitlePlaying, updateIsSubtitlePlaying } = useStore("useStore_IsSubtitlePlaying");
    const { currentSubtitlePlaybackMode, updateSubtitlePlaybackMode } = useStore("useStore_SubtitlePlaybackMode");
    const { currentSubtitleAbsoluteTargetTime, updateSubtitleAbsoluteTargetTime } = useStore("useStore_SubtitleAbsoluteTargetTime");
    const { currentIsCuesScheduled, updateIsCuesScheduled } = useStore("useStore_IsCuesScheduled");

    const { currentCountdownAdjustment, updateCountdownAdjustment } = useStore("useStore_CountdownAdjustment");
    const { currentEffectiveCountdown, updateEffectiveCountdown } = useStore("useStore_EffectiveCountdown");
    const { currentSubtitleCues, updateSubtitleCues } = useStore("useStore_SubtitleCues");

    // タイマー（setTimeout/setInterval）のID管理用
    const { currentSubtitleTimers, updateSubtitleTimers, addSubtitleTimers } = useStore("useStore_SubtitleTimers");
    // const timersRef = useRef([]);
    // カウントダウンタイマー専用の ref
    const { currentSubtitleCountdownTimerId, updateSubtitleCountdownTimerId, AddSubtitleCountdownTimerId } = useStore("useStore_SubtitleCountdownTimerId");

    // cues のスケジュールを行う（字幕開始時のオフセットは調整後のタイミングに合わせる）
    const scheduleCues = (offset) => {
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

        currentSubtitleCues.data.forEach((cue) => {
            const startDelay = cue.startTime * 1000 + offset;
            const endDelay = cue.endTime * 1000 + offset;
            if (startDelay >= 0) {
                const timerId = setTimeout(() => startFunction(cue), startDelay);
                addSubtitleTimers(timerId);
            }
            if (endDelay >= 0) {
                const timerId = setTimeout(() => endFunction(cue), endDelay);
                addSubtitleTimers(timerId);
            }
        });
    };


    // カウントダウンタイマーの開始／再登録（指定した値から1秒ごとに減らす）
    const startCountdownInterval = (startValue) => {
        // 既存のタイマーがあればクリア
        if (currentSubtitleCountdownTimerId.data) {
            clearInterval(currentSubtitleCountdownTimerId.data);
        }
        // 新たな開始値を設定
        updateEffectiveCountdown(startValue);
        const countdown_timer_id = setInterval(() => {
            updateEffectiveCountdown((prev) => {
                if (prev.data <= 1) {
                    clearInterval(currentSubtitleCountdownTimerId.data);
                    return 0;
                }
                return prev.data - 1;
            });
        }, 1000);
        updateSubtitleCountdownTimerId(countdown_timer_id);
        addSubtitleTimers(currentSubtitleCountdownTimerId.data);
    };


    //  字幕一覧の表示（relative モードの場合、クリックでジャンプ）
    // テーブル内の字幕行をクリック（relative モードのみ）でジャンプ
    const handleJump = (jumpCue) => {
        if (currentSubtitlePlaybackMode.data !== "relative") return;
        handleSubtitlesStop();
        const offset = -jumpCue.startTime * 1000;
        scheduleCues(offset);
        updateIsSubtitlePlaying(true);
    };



    // 「再生開始」ボタン押下時の処理
    const handleSubtitlesStart = () => {
        handleSubtitlesStop();
        updateIsSubtitlePlaying(true);
        updateIsCuesScheduled(false);
        const target_time = currentSubtitleAbsoluteTargetTime.data;

        let computedCountdown = 0;
        if (currentSubtitlePlaybackMode.data === "absolute") {
            const now = new Date();
            const hour = parseInt(target_time.hour, 10);
            const minute = parseInt(target_time.minute, 10);
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
        // setInitialCountdown(computedCountdown);
        // 調整値を反映した開始値
        const startValue = computedCountdown + currentCountdownAdjustment.data;
        startCountdownInterval(startValue);
        sendTextToOverlay(startValue.toString());
    };


    // すべてのタイマーを停止し、各状態を初期化する
    const handleSubtitlesStop = () => {
        currentSubtitleTimers.data.forEach((timerId) => {
            clearTimeout(timerId);
            clearInterval(timerId);
        });

        updateSubtitleTimers([]);
        if (currentSubtitleCountdownTimerId.data) {
            clearInterval(currentSubtitleCountdownTimerId.data);
            updateSubtitleCountdownTimerId(null);
        }
        console.log("再生を停止しました。");
        updateIsSubtitlePlaying(false);
        // setInitialCountdown(null);
        updateEffectiveCountdown(null);
        updateCountdownAdjustment(0);
        updateIsCuesScheduled(false);
    };


    return {
        currentSubtitleFileName,
        updateSubtitleFileName,

        currentIsSubtitlePlaying,
        updateIsSubtitlePlaying,

        currentSubtitlePlaybackMode,
        updateSubtitlePlaybackMode,

        currentSubtitleAbsoluteTargetTime,
        updateSubtitleAbsoluteTargetTime,

        currentIsCuesScheduled,
        updateIsCuesScheduled,

        currentCountdownAdjustment,
        updateCountdownAdjustment,

        currentEffectiveCountdown,
        updateEffectiveCountdown,

        currentSubtitleCues,
        updateSubtitleCues,

        handleSubtitlesStart,
        handleSubtitlesStop,
        startCountdownInterval,
        scheduleCues,
        handleJump,
    }

};