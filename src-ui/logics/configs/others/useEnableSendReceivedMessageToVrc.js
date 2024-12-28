import { useStore_EnableSendReceivedMessageToVrc } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableSendReceivedMessageToVrc = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableSendReceivedMessageToVrc, updateEnableSendReceivedMessageToVrc, pendingEnableSendReceivedMessageToVrc } = useStore_EnableSendReceivedMessageToVrc();

    const getEnableSendReceivedMessageToVrc = () => {
        pendingEnableSendReceivedMessageToVrc();
        asyncStdoutToPython("/get/data/send_received_message_to_vrc");
    };

    const toggleEnableSendReceivedMessageToVrc = () => {
        pendingEnableSendReceivedMessageToVrc();
        if (currentEnableSendReceivedMessageToVrc.data) {
            asyncStdoutToPython("/set/disable/send_received_message_to_vrc");
        } else {
            asyncStdoutToPython("/set/enable/send_received_message_to_vrc");
        }
    };

    return {
        currentEnableSendReceivedMessageToVrc,
        getEnableSendReceivedMessageToVrc,
        toggleEnableSendReceivedMessageToVrc,
        updateEnableSendReceivedMessageToVrc,
    };
};