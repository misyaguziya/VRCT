import { useStore_OverlaySettings } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useOverlaySettings = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentOverlaySettings, updateOverlaySettings, pendingOverlaySettings } = useStore_OverlaySettings();

    const getOverlaySettings = () => {
        // pendingOverlaySettings();
        asyncStdoutToPython("/get/data/overlay_settings");
    };

    const setOverlaySettings = (overlay_settings) => {
        // pendingOverlaySettings();
        asyncStdoutToPython("/set/data/overlay_settings", overlay_settings);
    };

    return {
        currentOverlaySettings,
        getOverlaySettings,
        updateOverlaySettings,
        setOverlaySettings,
    };
};