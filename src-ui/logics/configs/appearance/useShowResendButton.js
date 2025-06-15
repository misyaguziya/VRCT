import { useStore_ShowResendButton } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useShowResendButton = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentShowResendButton, updateShowResendButton, pendingShowResendButton } = useStore_ShowResendButton();

    const getShowResendButton = () => {
        pendingShowResendButton();
        asyncStdoutToPython("/get/data/show_resend_button");
    };

    const toggleShowResendButton = () => {
        pendingShowResendButton();
        if (currentShowResendButton.data) {
            asyncStdoutToPython("/set/disable/show_resend_button");
        } else {
            asyncStdoutToPython("/set/enable/show_resend_button");
        }
    };

    return {
        currentShowResendButton,
        getShowResendButton,
        updateShowResendButton,
        toggleShowResendButton,
    };
};