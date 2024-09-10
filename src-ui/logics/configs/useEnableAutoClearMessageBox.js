import { useEnableAutoClearMessageBox as useStoreEnableAutoClearMessageBox } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoClearMessageBox = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoClearMessageBox, updateEnableAutoClearMessageBox } = useStoreEnableAutoClearMessageBox();

    const getEnableAutoClearMessageBox = () => {
        updateEnableAutoClearMessageBox(() => new Promise(() => {}));
        asyncStdoutToPython("/config/enable_auto_clear_message_box");
    };

    const toggleEnableAutoClearMessageBox = () => {
        updateEnableAutoClearMessageBox(() => new Promise(() => {}));
        if (currentEnableAutoClearMessageBox.data) {
            asyncStdoutToPython("/controller/callback_disable_auto_clear_chatbox");
        } else {
            asyncStdoutToPython("/controller/callback_enable_auto_clear_chatbox");
        }
    };

    return {
        getEnableAutoClearMessageBox,
        toggleEnableAutoClearMessageBox,
        currentEnableAutoClearMessageBox,
        updateEnableAutoClearMessageBox
    };
};