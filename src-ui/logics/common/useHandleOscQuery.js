import { useI18n } from "@useI18n";
import {
    useNotificationStatus,
    useIsOscAvailable,
} from "@logics_common";

export const useHandleOscQuery = () => {
    const { t } = useI18n();
    const { showNotification_Warning } = useNotificationStatus();
    const { updateIsOscAvailable } = useIsOscAvailable();

    const handleOscQuery = (payload) => {
        const is_osc_query_enabled = payload.data;
        const disabled_functions = payload.disabled_functions;

        // OSC無効になるのは、OSC IP Addressが127.0.0.1、localhost以外の場合で発生。
        if (is_osc_query_enabled) {
            updateIsOscAvailable(true);

        } else { // OSC自体は無効だが、無効になった機能がない場合。
            updateIsOscAvailable(false);

            if (disabled_functions.length > 0) { // 無効になった機能がある場合は通知。
                const items_label = disabled_functions
                    .filter(fn => fn === "vrc_mic_mute_sync")
                    .map(() => `- ${t("config_page.others.vrc_mic_mute_sync.label")}`)
                    .join("\n");

                if (items_label) {
                    const message = `${t("common_warning.unable_to_use_osc_query")}\n${items_label}`;
                    showNotification_Warning(message, { hide_duration: 10000 });
                }
            }
        }
    };

    return { handleOscQuery };
};