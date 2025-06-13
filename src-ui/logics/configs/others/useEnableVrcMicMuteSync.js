import { useStore_EnableVrcMicMuteSync } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useEnableVrcMicMuteSync = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableVrcMicMuteSync, updateEnableVrcMicMuteSync, pendingEnableVrcMicMuteSync } = useStore_EnableVrcMicMuteSync();

    const getEnableVrcMicMuteSync = () => {
        pendingEnableVrcMicMuteSync();
        asyncStdoutToPython("/get/data/vrc_mic_mute_sync");
    };

    const toggleEnableVrcMicMuteSync = () => {
        pendingEnableVrcMicMuteSync();
        if (currentEnableVrcMicMuteSync.data.is_enabled) {
            asyncStdoutToPython("/set/disable/vrc_mic_mute_sync");
        } else {
            asyncStdoutToPython("/set/enable/vrc_mic_mute_sync");
        }
    };

    const updateEnableVrcMicMuteSync_FromBackend = (payload) => {
        updateEnableVrcMicMuteSync((old_value) => {
            return {...old_value.data, is_enabled: payload};
        });
    };

    return {
        currentEnableVrcMicMuteSync,
        getEnableVrcMicMuteSync,
        toggleEnableVrcMicMuteSync,
        updateEnableVrcMicMuteSync,

        updateEnableVrcMicMuteSync_FromBackend,
    };
};