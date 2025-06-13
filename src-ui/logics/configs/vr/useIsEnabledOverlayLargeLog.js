import { useStore_IsEnabledOverlayLargeLog } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useIsEnabledOverlayLargeLog = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentIsEnabledOverlayLargeLog, updateIsEnabledOverlayLargeLog, pendingIsEnabledOverlayLargeLog } = useStore_IsEnabledOverlayLargeLog();

    const getIsEnabledOverlayLargeLog = () => {
        pendingIsEnabledOverlayLargeLog();
        asyncStdoutToPython("/get/data/overlay_large_log");
    };

    const toggleIsEnabledOverlayLargeLog = () => {
        pendingIsEnabledOverlayLargeLog();
        if (currentIsEnabledOverlayLargeLog.data) {
            asyncStdoutToPython("/set/disable/overlay_large_log");
        } else {
            asyncStdoutToPython("/set/enable/overlay_large_log");
        }
    };

    return {
        currentIsEnabledOverlayLargeLog,
        getIsEnabledOverlayLargeLog,
        updateIsEnabledOverlayLargeLog,
        toggleIsEnabledOverlayLargeLog,
    };
};