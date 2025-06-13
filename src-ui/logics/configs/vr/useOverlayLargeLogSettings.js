import { useStore_OverlayLargeLogSettings } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useOverlayLargeLogSettings = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentOverlayLargeLogSettings, updateOverlayLargeLogSettings, pendingOverlayLargeLogSettings } = useStore_OverlayLargeLogSettings();

    const getOverlayLargeLogSettings = () => {
        // pendingOverlayLargeLogSettings();
        asyncStdoutToPython("/get/data/overlay_large_log_settings");
    };

    const setOverlayLargeLogSettings = (overlay_large_log_settings) => {
        // pendingOverlayLargeLogSettings();
        asyncStdoutToPython("/set/data/overlay_large_log_settings", overlay_large_log_settings);
    };

    return {
        currentOverlayLargeLogSettings,
        getOverlayLargeLogSettings,
        updateOverlayLargeLogSettings,
        setOverlayLargeLogSettings,
    };
};