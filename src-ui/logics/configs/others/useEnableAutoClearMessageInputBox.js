import { useStore_EnableAutoClearMessageInputBox } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoClearMessageInputBox = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoClearMessageInputBox, updateEnableAutoClearMessageInputBox, pendingEnableAutoClearMessageInputBox } = useStore_EnableAutoClearMessageInputBox();

    const getEnableAutoClearMessageInputBox = () => {
        pendingEnableAutoClearMessageInputBox();
        asyncStdoutToPython("/get/data/auto_clear_message_box");
    };

    const toggleEnableAutoClearMessageInputBox = () => {
        pendingEnableAutoClearMessageInputBox();
        if (currentEnableAutoClearMessageInputBox.data) {
            asyncStdoutToPython("/set/disable/auto_clear_message_box");
        } else {
            asyncStdoutToPython("/set/enable/auto_clear_message_box");
        }
    };

    return {
        currentEnableAutoClearMessageInputBox,
        getEnableAutoClearMessageInputBox,
        toggleEnableAutoClearMessageInputBox,
        updateEnableAutoClearMessageInputBox,
    };
};