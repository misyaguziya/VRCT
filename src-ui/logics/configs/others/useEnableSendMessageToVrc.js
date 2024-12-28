import { useStore_EnableSendMessageToVrc } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableSendMessageToVrc = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableSendMessageToVrc, updateEnableSendMessageToVrc, pendingEnableSendMessageToVrc } = useStore_EnableSendMessageToVrc();

    const getEnableSendMessageToVrc = () => {
        pendingEnableSendMessageToVrc();
        asyncStdoutToPython("/get/data/send_message_to_vrc");
    };

    const toggleEnableSendMessageToVrc = () => {
        pendingEnableSendMessageToVrc();
        if (currentEnableSendMessageToVrc.data) {
            asyncStdoutToPython("/set/disable/send_message_to_vrc");
        } else {
            asyncStdoutToPython("/set/enable/send_message_to_vrc");
        }
    };

    return {
        currentEnableSendMessageToVrc,
        getEnableSendMessageToVrc,
        toggleEnableSendMessageToVrc,
        updateEnableSendMessageToVrc,
    };
};