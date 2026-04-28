import { useNotificationStatus } from "@logics_common";

export const useHandleNetworkConnection = () => {

    const { showNotification_Error } = useNotificationStatus();

    const handleNetworkConnection = (is_network_connected) => {
        if (!is_network_connected) {
            showNotification_Error("Network is not connected. Some of the function will not work.", {
                hide_duration: 8000,
            });
        }
    };

    return {
        handleNetworkConnection,
    };
};