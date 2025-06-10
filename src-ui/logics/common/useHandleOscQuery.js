import { useTranslation } from "react-i18next";
import { useNotificationStatus } from "@logics_common";
import { useEnableVrcMicMuteSync } from "@logics_configs";

export const useHandleOscQuery = () => {
    const { t } = useTranslation();
    const { showNotification_Warning } = useNotificationStatus();
    const { updateEnableVrcMicMuteSync } = useEnableVrcMicMuteSync();

    const handleOscQuery = ({ is_osc_query_enabled, disabled_functions }) => {
        if (is_osc_query_enabled) {
            updateEnableVrcMicMuteSync(prev => ({
                ...prev.data,
                is_available: true,
            }));
            return;
        }

        if (!disabled_functions.length) {
            updateEnableVrcMicMuteSync(prev => ({
                ...prev.data,
                is_available: false,
            }));
            return;
        }

        const items_label = disabled_functions
            .filter(fn => fn === "vrc_mic_mute_sync")
            .map(() => `- ${t("config_page.others.vrc_mic_mute_sync.label")}`)
            .join("\n");

        updateEnableVrcMicMuteSync({
            is_enabled: false,
            is_available: false,
        });

        if (items_label) {
            const message = `${t("common_warning.unable_to_use_osc_query")}\n${items_label}`;
            showNotification_Warning(message, { hide_duration: 10000 });
        }
    };

    return { handleOscQuery };
};