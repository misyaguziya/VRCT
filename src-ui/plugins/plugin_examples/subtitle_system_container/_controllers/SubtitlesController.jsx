import { useStoreContext } from "../../store/store.js";

import { useSubtitles } from "../_logics/useSubtitles";
import { secToDayTime } from "../_subtitles_utils"
import { useEffect } from "react";
export const SubtitlesController = () => {
    const logic_configs = useStoreContext();
    const { sendTextToOverlay } = logic_configs.useSendTextToOverlay();

    const {
        currentIsSubtitlePlaying,
        currentIsCuesScheduled,
        updateIsCuesScheduled,
        currentCountdownAdjustment,
        currentEffectiveCountdown,
        scheduleCues,
    } = useSubtitles();

    // currentEffectiveCountdown.data が 0 になったとき、字幕開始
    useEffect(() => {
        if (
            currentIsSubtitlePlaying.data &&
            currentEffectiveCountdown.data !== null &&
            currentEffectiveCountdown.data <= 0 &&
            !currentIsCuesScheduled.data
        ) {
            sendTextToOverlay("スタート！");
            console.log("スタート！");
            // 調整後のタイミングで字幕スケジュールを開始
            scheduleCues(0);
            updateIsCuesScheduled(true);
        }

        if (currentEffectiveCountdown.data > 0) {
            console.log(secToDayTime(currentEffectiveCountdown.data));
            sendTextToOverlay(secToDayTime(currentEffectiveCountdown.data));
        }

    }, [currentEffectiveCountdown.data, currentIsSubtitlePlaying.data, currentIsCuesScheduled.data, currentCountdownAdjustment.data]);

    return null;
};