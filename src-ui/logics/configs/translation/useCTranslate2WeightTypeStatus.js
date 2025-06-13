import { useStore_CTranslate2WeightTypeStatus } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useCTranslate2WeightTypeStatus = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentCTranslate2WeightTypeStatus, updateCTranslate2WeightTypeStatus, pendingCTranslate2WeightTypeStatus } = useStore_CTranslate2WeightTypeStatus();

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

    return {
        currentCTranslate2WeightTypeStatus,
        updateCTranslate2WeightTypeStatus,

        updateDownloadedCTranslate2WeightTypeStatus,
        updateDownloadProgressCTranslate2WeightTypeStatus,
        pendingCTranslate2WeightType,
        downloadedCTranslate2WeightType,
        downloadCTranslate2Weight,
    };
};