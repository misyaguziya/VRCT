import { useStore_DeepLAuthKey } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useDeepLAuthKey = () => {
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

    return {
        currentDeepLAuthKey,
        getDeepLAuthKey,
        updateDeepLAuthKey,
        setDeepLAuthKey,
        deleteDeepLAuthKey,
    };
};