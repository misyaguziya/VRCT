import React, { useState, useRef, useEffect } from "react";
import styles from "./CountdownContainer.module.scss";
import { secToDayTime } from "../_subtitles_utils";
import { useSubtitles } from "../_logics/useSubtitles";

export const CountdownContainer = () => {
    const {
        updateCountdownAdjustment,
        currentEffectiveCountdown,
        currentIsCuesScheduled,
        startCountdownInterval,
    } = useSubtitles();
    // カウントダウン表示：字幕開始前は常に表示

    // if (currentEffectiveCountdown.data === 0) return null;
    if (currentEffectiveCountdown.data === null && currentIsCuesScheduled.data) return null;

    return (
        <div className={styles.container}>
            <span>カウントダウン: {secToDayTime(currentEffectiveCountdown.data)}</span>
            <div className={styles.adjust_button_container}>
                {/* 1分単位の調整ボタン */}
                <div className={styles.adjust_button_wrapper}>
                    <button
                        onClick={() => {
                            const newValue = currentEffectiveCountdown.data + 60;
                            updateCountdownAdjustment((prev) => prev.data + 60);
                            startCountdownInterval(newValue);
                        }}
                        className={styles.adjust_button}
                        >
                        ▲ 1分
                    </button>
                    <button
                        onClick={() => {
                            const newValue = currentEffectiveCountdown.data - 60;
                            updateCountdownAdjustment((prev) => prev.data - 60);
                            startCountdownInterval(newValue);
                        }}
                        className={styles.adjust_button}
                        >
                        ▼ 1分
                    </button>
                </div>
                <div className={styles.adjust_button_border}></div>
                {/* 1秒単位の調整ボタン */}
                <div className={styles.adjust_button_wrapper}>
                    <button
                        onClick={() => {
                            const newValue = currentEffectiveCountdown.data + 1;
                            updateCountdownAdjustment((prev) => prev.data + 1);
                            startCountdownInterval(newValue);
                        }}
                        className={styles.adjust_button}
                    >
                        ▲ 1秒
                    </button>
                    <button
                        onClick={() => {
                            const newValue = currentEffectiveCountdown.data - 1;
                            updateCountdownAdjustment((prev) => prev.data - 1);
                            startCountdownInterval(newValue);
                        }}
                        className={styles.adjust_button}
                    >
                        ▼ 1秒
                    </button>
                </div>
            </div>
        </div>
    );
};