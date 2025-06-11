import { useStore_SendMessageButtonType } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useSendMessageButtonType = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSendMessageButtonType, updateSendMessageButtonType, pendingSendMessageButtonType } = useStore_SendMessageButtonType();

    const getSendMessageButtonType = () => {
        pendingSendMessageButtonType();
        asyncStdoutToPython("/get/data/send_message_button_type");
    };

    const setSendMessageButtonType = (selected_type) => {
        pendingSendMessageButtonType();
        asyncStdoutToPython("/set/data/send_message_button_type", selected_type);
    };

    return {
        currentSendMessageButtonType,
        getSendMessageButtonType,
        setSendMessageButtonType,
        updateSendMessageButtonType,
    };
};