import { useStore_MessageLogUiScaling } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useMessageLogUiScaling = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMessageLogUiScaling, updateMessageLogUiScaling, pendingMessageLogUiScaling } = useStore_MessageLogUiScaling();

    const getMessageLogUiScaling = () => {
        pendingMessageLogUiScaling();
        asyncStdoutToPython("/get/data/textbox_ui_scaling");
    };

    const setMessageLogUiScaling = (selected_ui_scaling) => {
        pendingMessageLogUiScaling();
        asyncStdoutToPython("/set/data/textbox_ui_scaling", selected_ui_scaling);
    };

    return {
        currentMessageLogUiScaling,
        getMessageLogUiScaling,
        updateMessageLogUiScaling,
        setMessageLogUiScaling,
    };
};