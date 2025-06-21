import { useStore_NotificationStatus } from "@store";
import { useI18n } from "@useI18n";

export const useNotificationStatus = () => {
    const { currentNotificationStatus, updateNotificationStatus } = useStore_NotificationStatus();
    const { t } = useI18n();

    const showNotification_Warning = (message, options = {}) => {
        updateNotificationStatus({
            status: "warning",
            is_open: true,
            category_id: (options.category_id) ? options.category_id : null,
            message: message,
            options: options,
        });
    };

    const showNotification_Error = (message, options = {}) => {
        updateNotificationStatus({
            status: "error",
            is_open: true,
            category_id: (options.category_id) ? options.category_id : null,
            message: message,
            options: options,
        });
    };

    const showNotification_Success = (message, options = {}) => {
        updateNotificationStatus({
            status: "success",
            is_open: true,
            category_id: (options.category_id) ? options.category_id : null,
            message: message,
            options: options,
        });
    };

    const showNotification_SaveSuccess = (options = {}) => {
        options = { hide_duration: 1000, to_hide_progress_bar: true, ...options };
        updateNotificationStatus({
            status: "success",
            is_open: true,
            category_id: "save_success",
            message: t("config_page.notifications.save_success"),
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
        showNotification_SaveSuccess,
        closeNotification,
    };
};