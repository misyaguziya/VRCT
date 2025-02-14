import styles from "./ModeSelectorContainer.module.scss";
import { useSubtitles } from "../_logics/useSubtitles";
export const ModeSelectorContainer = () => {
    const {
        currentSubtitlePlaybackMode,
        updateSubtitlePlaybackMode,
        currentSubtitleAbsoluteTargetTime,
        updateSubtitleAbsoluteTargetTime,
    } = useSubtitles();

    const target_time = currentSubtitleAbsoluteTargetTime.data;

    const handleOnchangeTargetTime = (key, value) => {
        updateSubtitleAbsoluteTargetTime((old_value) => {
            return {
                ...old_value.data,
                [key]: value,
            }
        });
    };


    return (
        <div className={styles.container}>
            <div className={styles.mode_selector_wrapper}>
                <select
                    value={currentSubtitlePlaybackMode.data}
                    onChange={(e) => updateSubtitlePlaybackMode(e.target.value)}
                    className={styles.mode_selector}
                >
                    <option className={styles.mode_selector_item} value="relative">相対モード（ボタン押下から）</option>
                    <option className={styles.mode_selector_item} value="absolute">絶対モード（指定時刻から）</option>
                </select>
            </div>

            {currentSubtitlePlaybackMode.data === "absolute" && (
                <div className={styles.time_section}>
                    <label className={styles.absolute_time_label}>再生開始時刻 (HH:MM):</label>
                    <div className={styles.time_selects}>
                        <select
                            value={target_time.hour}
                            onChange={(e) => handleOnchangeTargetTime("hour", e.target.value)}
                            className={styles.time_selects_item}
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
                            value={target_time.minute}
                            onChange={(e) => handleOnchangeTargetTime("minute", e.target.value)}
                            className={styles.time_selects_item}
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
    );
};