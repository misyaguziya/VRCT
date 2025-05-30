import { useTranslation } from "react-i18next";
import { useNotificationStatus } from "@logics_common";
import {
    useEnableVrcMicMuteSync,
} from "@logics_configs";

export const useHandleOscQuery = () => {
    const { t } = useTranslation();

    const { showNotification_Warning } = useNotificationStatus();
    const { updateEnableVrcMicMuteSync } = useEnableVrcMicMuteSync();

    const handleOscQuery = ({is_osc_query_enabled, disabled_functions}) => {
        if (!is_osc_query_enabled && disabled_functions.length > 0) {
            const BASE_LABEL = t("common_warning.unable_to_use_osc_query");
            let items_label = "";

            for (const disabled_function of disabled_functions) {
                if (disabled_function === "vrc_mic_mute_sync") {
                    updateEnableVrcMicMuteSync({
                        is_enabled: false,
                        is_available: false,
                    });
                    const item = `- ${t("config_page.others.vrc_mic_mute_sync.label")}`;
                    items_label = `${items_label}\n${item}`;
                }
            }
            const label = `${BASE_LABEL}${items_label}`;
            showNotification_Warning(
                label,
                { hide_duration: 10000, }
            );
        } else if (is_osc_query_enabled) {
            updateEnableVrcMicMuteSync((old_value) => ({
                ...old_value.data,
                is_available: true,
            }));
        }
    };

    return {
        handleOscQuery,
    };
};