import { useStore_IsVisibleResendButton } from "@store";

export const useIsVisibleResendButton = () => {
    const { currentIsVisibleResendButton, updateIsVisibleResendButton } = useStore_IsVisibleResendButton();

    const toggleIsVisibleResendButton = () => {
        updateIsVisibleResendButton(!currentIsVisibleResendButton.data);
    };

    return {
        currentIsVisibleResendButton,
        toggleIsVisibleResendButton,
        updateIsVisibleResendButton,
    };
};