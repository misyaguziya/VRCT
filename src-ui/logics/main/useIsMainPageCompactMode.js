import { useStore_IsMainPageCompactMode } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useIsMainPageCompactMode = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentIsMainPageCompactMode, updateIsMainPageCompactMode } = useStore_IsMainPageCompactMode();

    const getIsMainPageCompactMode = () => {
        asyncStdoutToPython("/get/data/main_window_sidebar_compact_mode");
    };

    const toggleIsMainPageCompactMode = () => {
        if (currentIsMainPageCompactMode.data) {
            asyncStdoutToPython("/set/disable/main_window_sidebar_compact_mode");
        } else {
            asyncStdoutToPython("/set/enable/main_window_sidebar_compact_mode");
        }
    };

    return {
        currentIsMainPageCompactMode,
        getIsMainPageCompactMode,
        toggleIsMainPageCompactMode,
        updateIsMainPageCompactMode,
    };
};