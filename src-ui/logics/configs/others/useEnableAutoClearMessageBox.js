import { useStore_EnableAutoClearMessageBox } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoClearMessageBox = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoClearMessageBox, updateEnableAutoClearMessageBox, pendingEnableAutoClearMessageBox } = useStore_EnableAutoClearMessageBox();

    const getEnableAutoClearMessageBox = () => {
        pendingEnableAutoClearMessageBox();
        asyncStdoutToPython("/get/data/auto_clear_message_box");
    };

    const toggleEnableAutoClearMessageBox = () => {
        pendingEnableAutoClearMessageBox();
        if (currentEnableAutoClearMessageBox.data) {
            asyncStdoutToPython("/set/disable/auto_clear_message_box");
        } else {
            asyncStdoutToPython("/set/enable/auto_clear_message_box");
        }
    };

    return {
        currentEnableAutoClearMessageBox,
        getEnableAutoClearMessageBox,
        toggleEnableAutoClearMessageBox,
        updateEnableAutoClearMessageBox,
    };
};