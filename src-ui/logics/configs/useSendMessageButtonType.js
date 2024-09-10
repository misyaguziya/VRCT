import { useSendMessageButtonType as useStoreSendMessageButtonType } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSendMessageButtonType = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSendMessageButtonType, updateSendMessageButtonType } = useStoreSendMessageButtonType();

    const getSendMessageButtonType = () => {
        updateSendMessageButtonType(() => new Promise(() => {}));
        asyncStdoutToPython("/config/send_message_button_type");
    };

    const setSendMessageButtonType = (selected_type) => {
        updateSendMessageButtonType(() => new Promise(() => {}));
        asyncStdoutToPython("/controller/callback_set_send_message_button_type", selected_type);
    };

    return {
        getSendMessageButtonType,
        setSendMessageButtonType,
        currentSendMessageButtonType,
        updateSendMessageButtonType
    };
};