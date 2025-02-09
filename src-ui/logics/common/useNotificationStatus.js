import { useStore_NotificationStatus } from "@store";

export const useNotificationStatus = () => {
    const { currentNotificationStatus, updateNotificationStatus } = useStore_NotificationStatus();

    const generateRandomKey = () => Math.random();

    const showNotification_Error = (message, options = {}) => {
        updateNotificationStatus({
            status: "error",
            is_open: true,
            key: generateRandomKey(),
            message: message,
            options: options,
        });
    };

    const showNotification_Success = (message) => {
        updateNotificationStatus({
            status: "success",
            is_open: true,
            key: generateRandomKey(),
            message: message,
            options: options,
        });
    };

    const closeNotification = (event, reason) => {
        if (reason === "clickaway") return;
        updateNotificationStatus((prev) => ({
            ...prev.data,
            is_open: false,
        }));
    };

    return {
        currentNotificationStatus,
        updateNotificationStatus,

        showNotification_Error,
        showNotification_Success,
        closeNotification,
    };
};