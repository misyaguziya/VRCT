import {
    useStore_CTranslate2WeightTypeStatus,
    useStore_SelectedCTranslate2WeightType,
    useStore_SelectableCTranslate2ComputeDeviceList,
    useStore_SelectedCTranslate2ComputeDevice,
    useStore_DeepLAuthKey,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useI18n } from "@useI18n";
import { transformToIndexedArray } from "@utils";
import { useNotificationStatus } from "@logics_common";

export const useTranslation = () => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    const { showNotification_SaveSuccess } = useNotificationStatus();

    const { currentCTranslate2WeightTypeStatus, updateCTranslate2WeightTypeStatus, pendingCTranslate2WeightTypeStatus } = useStore_CTranslate2WeightTypeStatus();
    const { currentSelectedCTranslate2WeightType, updateSelectedCTranslate2WeightType, pendingSelectedCTranslate2WeightType } = useStore_SelectedCTranslate2WeightType();
    const { currentSelectableCTranslate2ComputeDeviceList, updateSelectableCTranslate2ComputeDeviceList, pendingSelectableCTranslate2ComputeDeviceList } = useStore_SelectableCTranslate2ComputeDeviceList();
    const { currentSelectedCTranslate2ComputeDevice, updateSelectedCTranslate2ComputeDevice, pendingSelectedCTranslate2ComputeDevice } = useStore_SelectedCTranslate2ComputeDevice();
    const { currentDeepLAuthKey, updateDeepLAuthKey, pendingDeepLAuthKey } = useStore_DeepLAuthKey();


    const updateDownloadedCTranslate2WeightTypeStatus = (downloaded_weight_type_status) => {
        updateCTranslate2WeightTypeStatus((old_status) =>
            old_status.data.map((item) => ({
                ...item,
                is_downloaded: downloaded_weight_type_status[item.id] ?? item.is_downloaded,
            }))
        );
    };
    const updateDownloadProgressCTranslate2WeightTypeStatus = (payload) => {
        if (payload === true) return console.error("fix me.");

        updateCTranslate2WeightTypeStatus((old_status) =>
            old_status.data.map((item) =>
                payload.weight_type === item.id
                    ? { ...item, progress: payload.progress * 100 }
                    : item
            )
        );
    };
    const pendingCTranslate2WeightType = (id) => {
        updateCTranslate2WeightTypeStatus((old_status) =>
            old_status.data.map((item) =>
                id === item.id
                    ? { ...item, is_pending: true }
                    : item
            )
        );
    };
    const downloadedCTranslate2WeightType = (id) => {
        updateCTranslate2WeightTypeStatus((old_status) =>
            old_status.data.map((item) =>
                id === item.id
                    ? { ...item, is_downloaded: true, is_pending: false, progress: null }
                    : item
            )
        );
    };
    const downloadCTranslate2Weight = (weight_type) => {
        asyncStdoutToPython("/run/download_ctranslate2_weight", weight_type);
    };


    const getSelectedCTranslate2WeightType = () => {
        pendingSelectedCTranslate2WeightType();
        asyncStdoutToPython("/get/data/ctranslate2_weight_type");
    };

    const setSelectedCTranslate2WeightType = (selected_ctranslate2_weight_type) => {
        pendingSelectedCTranslate2WeightType();
        asyncStdoutToPython("/set/data/ctranslate2_weight_type", selected_ctranslate2_weight_type);
    };

    const setSuccessSelectedCTranslate2WeightType = (selected_ctranslate2_weight_type) => {
        updateSelectedCTranslate2WeightType(selected_ctranslate2_weight_type);
        showNotification_SaveSuccess();
    };


    const getSelectableCTranslate2ComputeDeviceList = () => {
        pendingSelectableCTranslate2ComputeDeviceList();
        asyncStdoutToPython("/get/data/translation_compute_device_list");
    };

    const updateSelectableCTranslate2ComputeDeviceList_FromBackend = (payload) => {
        updateSelectableCTranslate2ComputeDeviceList(transformToIndexedArray(payload));
    };


    const getSelectedCTranslate2ComputeDevice = () => {
        pendingSelectedCTranslate2ComputeDevice();
        asyncStdoutToPython("/get/data/selected_translation_compute_device");
    };

    const setSelectedCTranslate2ComputeDevice = (selected_translation_compute_device) => {
        pendingSelectedCTranslate2ComputeDevice();
        asyncStdoutToPython("/set/data/selected_translation_compute_device", selected_translation_compute_device);
    };

    const setSuccessSelectedCTranslate2ComputeDevice = (selected_translation_compute_device) => {
        updateSelectedCTranslate2ComputeDevice(selected_translation_compute_device);
        showNotification_SaveSuccess();
    };


    const getDeepLAuthKey = () => {
        pendingDeepLAuthKey();
        asyncStdoutToPython("/get/data/deepl_auth_key");
    };

    const setDeepLAuthKey = (selected_deepl_auth_key) => {
        pendingDeepLAuthKey();
        asyncStdoutToPython("/set/data/deepl_auth_key", selected_deepl_auth_key);
    };

    const setSuccessDeepLAuthKey = (data) => {
        updateDeepLAuthKey(data);
        showNotification_SaveSuccess(t("config_page.translation.deepl_auth_key.auth_key_success"), { category_id: "deepl_auth_key" });
    };

    const deleteDeepLAuthKey = () => {
        pendingDeepLAuthKey();
        asyncStdoutToPython("/delete/data/deepl_auth_key");
    };

    const deleteSuccessDeepLAuthKey = () => {
        updateDeepLAuthKey("");
    };


    return {
        currentCTranslate2WeightTypeStatus,
        updateCTranslate2WeightTypeStatus,
        updateDownloadedCTranslate2WeightTypeStatus,
        updateDownloadProgressCTranslate2WeightTypeStatus,
        pendingCTranslate2WeightType,
        downloadedCTranslate2WeightType,
        downloadCTranslate2Weight,

        currentSelectedCTranslate2WeightType,
        getSelectedCTranslate2WeightType,
        updateSelectedCTranslate2WeightType,
        setSelectedCTranslate2WeightType,
        setSuccessSelectedCTranslate2WeightType,

        currentSelectableCTranslate2ComputeDeviceList,
        getSelectableCTranslate2ComputeDeviceList,
        updateSelectableCTranslate2ComputeDeviceList,
        updateSelectableCTranslate2ComputeDeviceList_FromBackend,

        currentSelectedCTranslate2ComputeDevice,
        getSelectedCTranslate2ComputeDevice,
        updateSelectedCTranslate2ComputeDevice,
        setSelectedCTranslate2ComputeDevice,
        setSuccessSelectedCTranslate2ComputeDevice,

        currentDeepLAuthKey,
        getDeepLAuthKey,
        updateDeepLAuthKey,
        setDeepLAuthKey,
        deleteDeepLAuthKey,
        deleteSuccessDeepLAuthKey,
        setSuccessDeepLAuthKey,
    };
};