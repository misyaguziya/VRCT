import { useStore_DeepLAuthKey } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useTranslation } from "react-i18next";
import { useNotificationStatus } from "@logics_common";

export const useDeepLAuthKey = () => {
    const { t } = useTranslation();
    const { showNotification_Success, showNotification_Error } = useNotificationStatus();
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentDeepLAuthKey, updateDeepLAuthKey, pendingDeepLAuthKey } = useStore_DeepLAuthKey();

    const getDeepLAuthKey = () => {
        pendingDeepLAuthKey();
        asyncStdoutToPython("/get/data/deepl_auth_key");
    };

    const setDeepLAuthKey = (selected_deepl_auth_key) => {
        pendingDeepLAuthKey();
        asyncStdoutToPython("/set/data/deepl_auth_key", selected_deepl_auth_key);
    };

    const deleteDeepLAuthKey = () => {
        pendingDeepLAuthKey();
        asyncStdoutToPython("/delete/data/deepl_auth_key");
    };
    const deletedDeepLAuthKey = () => {
        updateDeepLAuthKey("");
    };

    const savedDeepLAuthKey = (data) => {
        updateDeepLAuthKey(data);
        showNotification_Success(t("config_page.translation.deepl_auth_key.auth_key_success"));
    };

    return {
        currentDeepLAuthKey,
        getDeepLAuthKey,
        updateDeepLAuthKey,
        setDeepLAuthKey,
        deleteDeepLAuthKey,

        deletedDeepLAuthKey,
        savedDeepLAuthKey,
    };
};