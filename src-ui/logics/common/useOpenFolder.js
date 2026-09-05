import { useStdoutToPython } from "@useStdoutToPython";
import { useNotificationStatus } from "@logics_common";
import { useI18n } from "@useI18n";

export const useOpenFolder = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { showNotification_Success } = useNotificationStatus();
    const { t } = useI18n();

    const openFolder_MessageLogs = () => {
        asyncStdoutToPython("/run/open_filepath_logs");
    };
    const openedFolder_MessageLogs = () => {
        showNotification_Success(t("config_page.notifications.opened_folder"), {
            category_id: "opened_folder",
            hide_duration: 2000,
            to_hide_progress_bar: true,
        });
    };

    const openFolder_ConfigFile = () => {
        asyncStdoutToPython("/run/open_filepath_config_file");
    };
    const openedFolder_ConfigFile = () => {
        showNotification_Success(t("config_page.notifications.opened_folder"), {
            category_id: "opened_folder",
            hide_duration: 2000,
            to_hide_progress_bar: true,
        });
    };

    return {
        openFolder_MessageLogs,
        openFolder_ConfigFile,

        openedFolder_MessageLogs,
        openedFolder_ConfigFile,
    };
};