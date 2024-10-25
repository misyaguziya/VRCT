import { useStore_OverlaySmallLogSettings } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useOverlaySmallLogSettings = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentOverlaySmallLogSettings, updateOverlaySmallLogSettings, pendingOverlaySmallLogSettings } = useStore_OverlaySmallLogSettings();

    const getOverlaySmallLogSettings = () => {
        // pendingOverlaySmallLogSettings();
        asyncStdoutToPython("/get/data/overlay_small_log_settings");
    };

    const setOverlaySmallLogSettings = (overlay_small_log_settings) => {
        // pendingOverlaySmallLogSettings();
        asyncStdoutToPython("/set/data/overlay_small_log_settings", overlay_small_log_settings);
    };

    return {
        currentOverlaySmallLogSettings,
        getOverlaySmallLogSettings,
        updateOverlaySmallLogSettings,
        setOverlaySmallLogSettings,
    };
};