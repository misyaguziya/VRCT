import { useI18n } from "@useI18n";
import { useNotificationStatus } from "@logics_common";
import { useOthers } from "@logics_configs";

export const useHandleOscQuery = () => {
    const { t } = useI18n();
    const { showNotification_Warning } = useNotificationStatus();
    const { updateEnableVrcMicMuteSync } = useOthers();

    const handleOscQuery = (payload) => {
        const is_osc_query_enabled = payload.data;
        const disabled_functions = payload.disabled_functions;

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