// import React, { useState, useRef, useEffect } from "react";
import styles from "./PlayControlContainer.module.scss";
import { useSubtitles } from "../_logics/useSubtitles";
import clsx from "clsx";

export const PlayControlContainer = () => {
    const {
        currentIsSubtitlePlaying,
        handleSubtitlesStart,
        handleSubtitlesStop,
    } = useSubtitles();

    const is_playing = currentIsSubtitlePlaying.data;

    const playback_button_classname = clsx(styles.playback_button, {
        [styles.is_playing]: is_playing,
    });
    return (
        <div className={styles.container}>
            <button
                onClick={handleSubtitlesStart}
                className={playback_button_classname}
            >
                {is_playing ? "再生中" : "字幕を登録・再生"}
            </button>
            {is_playing &&
                <button onClick={handleSubtitlesStop} className={styles.playback_stop_button}>
                    停止
                </button>
            }
        </div>
    );
};