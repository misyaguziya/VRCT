import { useStore_SendMessageButtonType } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSendMessageButtonType = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSendMessageButtonType, updateSendMessageButtonType } = useStore_SendMessageButtonType();

    const getSendMessageButtonType = () => {
        updateSendMessageButtonType(() => new Promise(() => {}));
        asyncStdoutToPython("/get/send_message_button_type");
    };

    const setSendMessageButtonType = (selected_type) => {
        updateSendMessageButtonType(() => new Promise(() => {}));
        asyncStdoutToPython("/set/send_message_button_type", selected_type);
    };

    return {
        currentSendMessageButtonType,
        getSendMessageButtonType,
        setSendMessageButtonType,
        updateSendMessageButtonType,
    };
};