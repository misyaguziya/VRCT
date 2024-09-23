import { useStore_IsMainPageCompactMode } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useIsMainPageCompactMode = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentIsMainPageCompactMode, updateIsMainPageCompactMode } = useStore_IsMainPageCompactMode();

    const getIsMainPageCompactMode = () => {
        asyncStdoutToPython("/get/main_window_sidebar_compact_mode");
    };

    const toggleIsMainPageCompactMode = () => {
        if (currentIsMainPageCompactMode.data) {
            asyncStdoutToPython("/set/disable_main_window_sidebar_compact_mode");
        } else {
            asyncStdoutToPython("/set/enable_main_window_sidebar_compact_mode");
        }
    };

    return {
        currentIsMainPageCompactMode,
        getIsMainPageCompactMode,
        toggleIsMainPageCompactMode,
        updateIsMainPageCompactMode,
    };
};