import { useStore_UiScaling } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useUiScaling = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentUiScaling, updateUiScaling, pendingUiScaling } = useStore_UiScaling();

    const getUiScaling = () => {
        pendingUiScaling();
        asyncStdoutToPython("/get/data/ui_scaling");
    };

    const setUiScaling = (selected_ui_scaling) => {
        pendingUiScaling();
        asyncStdoutToPython("/set/data/ui_scaling", selected_ui_scaling);
    };

    return {
        currentUiScaling,
        getUiScaling,
        updateUiScaling,
        setUiScaling,
    };
};