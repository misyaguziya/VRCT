import { useStore_IsVrctAvailable } from "@store";
import { useNotificationStatus } from "@logics_common";

export const useIsVrctAvailable = () => {
    const { currentIsVrctAvailable, updateIsVrctAvailable } = useStore_IsVrctAvailable();
    const { showNotification_Success, showNotification_Error } = useNotificationStatus();

    const handleAiModelsAvailability = (is_ai_models_available) => {
        if (is_ai_models_available === false) {
            updateIsVrctAvailable(false);
            showNotification_Error("AI models have not been detected. Check the network connection and restart VRCT (it will download automatically, normally).", { hide_duration: null });
        }
    };

    return {
        currentIsVrctAvailable,
        updateIsVrctAvailable,

        handleAiModelsAvailability,
    };
};