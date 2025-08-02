import { useStore_IsVrctAvailable } from "@store";
import { useNotificationStatus } from "@logics_common";
import { HomepageLinkButton } from "@common_components";

export const useIsVrctAvailable = () => {
    const { currentIsVrctAvailable, updateIsVrctAvailable } = useStore_IsVrctAvailable();
    const { showNotification_Success, showNotification_Error } = useNotificationStatus();

    const handleAiModelsAvailability = (is_ai_models_available) => {
        if (is_ai_models_available === false) {
            updateIsVrctAvailable(false);
            const ErrorComponent = () => {
                return (
                    <div>
                        <p>AI models have not been detected. Check the network connection and restart VRCT (it will download automatically, normally).</p>
                        <p>If this error occurs frequently, try the following:</p>
                        <HomepageLinkButton
                            homepage_link="https://github.com/misyaguziya/VRCT/wiki/Manual-Installation-of-AI-Model-Weights"
                        />
                    </div>
                );
            };
            showNotification_Error(ErrorComponent, { hide_duration: null });
        }
    };

    return {
        currentIsVrctAvailable,
        updateIsVrctAvailable,

        handleAiModelsAvailability,
    };
};