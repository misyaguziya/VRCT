import { useStore_OverlayShowOnlyTranslatedMessages } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useOverlayShowOnlyTranslatedMessages = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentOverlayShowOnlyTranslatedMessages, updateOverlayShowOnlyTranslatedMessages, pendingOverlayShowOnlyTranslatedMessages } = useStore_OverlayShowOnlyTranslatedMessages();

    const getOverlayShowOnlyTranslatedMessages = () => {
        pendingOverlayShowOnlyTranslatedMessages();
        asyncStdoutToPython("/get/data/overlay_show_only_translated_messages");
    };

    const toggleOverlayShowOnlyTranslatedMessages = () => {
        pendingOverlayShowOnlyTranslatedMessages();
        if (currentOverlayShowOnlyTranslatedMessages.data) {
            asyncStdoutToPython("/set/disable/overlay_show_only_translated_messages");
        } else {
            asyncStdoutToPython("/set/enable/overlay_show_only_translated_messages");
        }
    };

    return {
        currentOverlayShowOnlyTranslatedMessages,
        getOverlayShowOnlyTranslatedMessages,
        updateOverlayShowOnlyTranslatedMessages,
        toggleOverlayShowOnlyTranslatedMessages,
    };
};