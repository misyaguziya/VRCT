import { useStore_NotificationStatus } from "@store";

export const useNotificationStatus = () => {
    const { currentNotificationStatus, updateNotificationStatus } = useStore_NotificationStatus();

    const generateRandomKey = () => Math.random();

    const showNotification_Warning = (message, options = {}) => {
        updateNotificationStatus({
            status: "warning",
            is_open: true,
            key: generateRandomKey(),
            message: message,
            options: options,
        });
    };

    const showNotification_Error = (message, options = {}) => {
        updateNotificationStatus({
            status: "error",
            is_open: true,
            key: generateRandomKey(),
            message: message,
            options: options,
        });
    };

    const showNotification_Success = (message, options = {}) => {
        updateNotificationStatus({
            status: "success",
            is_open: true,
            key: generateRandomKey(),
            message: message,
            options: options,
        });
    };

    const closeNotification = () => {
        updateNotificationStatus((prev) => ({
            ...prev.data,
            is_open: false,
        }));
    };

    return {
        currentNotificationStatus,
        updateNotificationStatus,

        showNotification_Warning,
        showNotification_Error,
        showNotification_Success,
        closeNotification,
    };
};