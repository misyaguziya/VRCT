import { useStore_EnableSendOnlyTranslatedMessages } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableSendOnlyTranslatedMessages = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableSendOnlyTranslatedMessages, updateEnableSendOnlyTranslatedMessages, pendingEnableSendOnlyTranslatedMessages } = useStore_EnableSendOnlyTranslatedMessages();

    const getEnableSendOnlyTranslatedMessages = () => {
        pendingEnableSendOnlyTranslatedMessages();
        asyncStdoutToPython("/get/data/send_only_translated_messages");
    };

    const toggleEnableSendOnlyTranslatedMessages = () => {
        pendingEnableSendOnlyTranslatedMessages();
        if (currentEnableSendOnlyTranslatedMessages.data) {
            asyncStdoutToPython("/set/disable/send_only_translated_messages");
        } else {
            asyncStdoutToPython("/set/enable/send_only_translated_messages");
        }
    };

    return {
        currentEnableSendOnlyTranslatedMessages,
        getEnableSendOnlyTranslatedMessages,
        toggleEnableSendOnlyTranslatedMessages,
        updateEnableSendOnlyTranslatedMessages,
    };
};