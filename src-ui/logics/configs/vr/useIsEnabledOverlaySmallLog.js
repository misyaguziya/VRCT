import { useStore_IsEnabledOverlaySmallLog } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useIsEnabledOverlaySmallLog = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentIsEnabledOverlaySmallLog, updateIsEnabledOverlaySmallLog, pendingIsEnabledOverlaySmallLog } = useStore_IsEnabledOverlaySmallLog();

    const getIsEnabledOverlaySmallLog = () => {
        pendingIsEnabledOverlaySmallLog();
        asyncStdoutToPython("/get/data/overlay_small_log");
    };

    const toggleIsEnabledOverlaySmallLog = () => {
        pendingIsEnabledOverlaySmallLog();
        if (currentIsEnabledOverlaySmallLog.data) {
            asyncStdoutToPython("/set/disable/overlay_small_log");
        } else {
            asyncStdoutToPython("/set/enable/overlay_small_log");
        }
    };

    return {
        currentIsEnabledOverlaySmallLog,
        getIsEnabledOverlaySmallLog,
        updateIsEnabledOverlaySmallLog,
        toggleIsEnabledOverlaySmallLog,
    };
};