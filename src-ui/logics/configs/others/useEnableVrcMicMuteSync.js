import { useStore_EnableVrcMicMuteSync } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableVrcMicMuteSync = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableVrcMicMuteSync, updateEnableVrcMicMuteSync, pendingEnableVrcMicMuteSync } = useStore_EnableVrcMicMuteSync();

    const getEnableVrcMicMuteSync = () => {
        pendingEnableVrcMicMuteSync();
        asyncStdoutToPython("/get/data/vrc_mic_mute_sync");
    };

    const toggleEnableVrcMicMuteSync = () => {
        pendingEnableVrcMicMuteSync();
        if (currentEnableVrcMicMuteSync.data) {
            asyncStdoutToPython("/set/disable/vrc_mic_mute_sync");
        } else {
            asyncStdoutToPython("/set/enable/vrc_mic_mute_sync");
        }
    };

    return {
        currentEnableVrcMicMuteSync,
        getEnableVrcMicMuteSync,
        toggleEnableVrcMicMuteSync,
        updateEnableVrcMicMuteSync,
    };
};