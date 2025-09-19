import {
    useStore_CTranslate2WeightTypeStatus,
    useStore_SelectedCTranslate2WeightType,
    useStore_SelectableCTranslate2ComputeTypeList,
    useStore_SelectedCTranslate2ComputeType,
    useStore_SelectableTranslationComputeDeviceList,
    useStore_SelectedTranslationComputeDevice,
    useStore_DeepLAuthKey,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useI18n } from "@useI18n";
import { transformToIndexedArray, arrayToObject } from "@utils";
import { useNotificationStatus } from "@logics_common";

export const useTranslation = () => {
    const { t } = useI18n();
    const { asyncStdoutToPython } = useStdoutToPython();
    const { showNotification_SaveSuccess } = useNotificationStatus();

    const { currentCTranslate2WeightTypeStatus, updateCTranslate2WeightTypeStatus, pendingCTranslate2WeightTypeStatus } = useStore_CTranslate2WeightTypeStatus();
    const { currentSelectedCTranslate2WeightType, updateSelectedCTranslate2WeightType, pendingSelectedCTranslate2WeightType } = useStore_SelectedCTranslate2WeightType();

    const { currentSelectableCTranslate2ComputeTypeList, updateSelectableCTranslate2ComputeTypeList, pendingSelectableCTranslate2ComputeTypeList } = useStore_SelectableCTranslate2ComputeTypeList();
    const { currentSelectedCTranslate2ComputeType, updateSelectedCTranslate2ComputeType, pendingSelectedCTranslate2ComputeType } = useStore_SelectedCTranslate2ComputeType();

    const { currentSelectableTranslationComputeDeviceList, updateSelectableTranslationComputeDeviceList, pendingSelectableTranslationComputeDeviceList } = useStore_SelectableTranslationComputeDeviceList();
    const { currentSelectedTranslationComputeDevice, updateSelectedTranslationComputeDevice, pendingSelectedTranslationComputeDevice } = useStore_SelectedTranslationComputeDevice();

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



    const getSelectableCTranslate2ComputeTypeList = () => {
        pendingSelectableCTranslate2ComputeTypeList();
        asyncStdoutToPython("/get/data/ctranslate2_compute_type_list");
    };

    const updateSelectableCTranslate2ComputeTypeList_FromBackend = (payload) => {
        updateSelectableCTranslate2ComputeTypeList(arrayToObject(payload));
    };


    const getSelectedCTranslate2ComputeType = () => {
        pendingSelectedCTranslate2ComputeType();
        asyncStdoutToPython("/get/data/ctranslate2_compute_type");
    };

    const setSelectedCTranslate2ComputeType = (selected_ctranslate2_compute_type) => {
        pendingSelectedCTranslate2ComputeType();
        asyncStdoutToPython("/set/data/ctranslate2_compute_type", selected_ctranslate2_compute_type);
    };

    const setSuccessSelectedCTranslate2ComputeType = (selected_ctranslate2_compute_type) => {
        updateSelectedCTranslate2ComputeType(selected_ctranslate2_compute_type);
        showNotification_SaveSuccess();
    };



    const getSelectableTranslationComputeDeviceList = () => {
        pendingSelectableTranslationComputeDeviceList();
        asyncStdoutToPython("/get/data/translation_compute_device_list");
    };

    const updateSelectableTranslationComputeDeviceList_FromBackend = (payload) => {
        updateSelectableTranslationComputeDeviceList(transformToIndexedArray(payload));
    };


    const getSelectedTranslationComputeDevice = () => {
        pendingSelectedTranslationComputeDevice();
        asyncStdoutToPython("/get/data/selected_translation_compute_device");
    };

    const setSelectedTranslationComputeDevice = (selected_translation_compute_device) => {
        pendingSelectedTranslationComputeDevice();
        asyncStdoutToPython("/set/data/selected_translation_compute_device", selected_translation_compute_device);
    };

    const setSuccessSelectedTranslationComputeDevice = (selected_translation_compute_device) => {
        updateSelectedTranslationComputeDevice(selected_translation_compute_device);
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


        currentSelectableCTranslate2ComputeTypeList,
        getSelectableCTranslate2ComputeTypeList,
        updateSelectableCTranslate2ComputeTypeList,
        updateSelectableCTranslate2ComputeTypeList_FromBackend,

        currentSelectedCTranslate2ComputeType,
        getSelectedCTranslate2ComputeType,
        updateSelectedCTranslate2ComputeType,
        setSelectedCTranslate2ComputeType,
        setSuccessSelectedCTranslate2ComputeType,


        currentSelectableTranslationComputeDeviceList,
        getSelectableTranslationComputeDeviceList,
        updateSelectableTranslationComputeDeviceList,
        updateSelectableTranslationComputeDeviceList_FromBackend,

        currentSelectedTranslationComputeDevice,
        getSelectedTranslationComputeDevice,
        updateSelectedTranslationComputeDevice,
        setSelectedTranslationComputeDevice,
        setSuccessSelectedTranslationComputeDevice,

        currentDeepLAuthKey,
        getDeepLAuthKey,
        updateDeepLAuthKey,
        setDeepLAuthKey,
        deleteDeepLAuthKey,
        deleteSuccessDeepLAuthKey,
        setSuccessDeepLAuthKey,
    };
};