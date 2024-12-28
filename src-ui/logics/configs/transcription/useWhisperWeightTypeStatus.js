import { useStore_WhisperWeightTypeStatus } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useWhisperWeightTypeStatus = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentWhisperWeightTypeStatus, updateWhisperWeightTypeStatus, pendingWhisperWeightTypeStatus } = useStore_WhisperWeightTypeStatus();

    const updateDownloadedWhisperWeightTypeStatus = (downloaded_weight_type_status) => {
        updateWhisperWeightTypeStatus((old_status) =>
            old_status.data.map((item) => ({
                ...item,
                is_downloaded: downloaded_weight_type_status[item.id] ?? item.is_downloaded,
            }))
        );
    };
    const updateDownloadProgressWhisperWeightTypeStatus = (payload) => {
        if (payload === true) return console.error("fix me.");

        updateWhisperWeightTypeStatus((old_status) =>
            old_status.data.map((item) =>
                payload.weight_type === item.id
                    ? { ...item, progress: payload.progress * 100 }
                    : item
            )
        );
    };
    const pendingWhisperWeightType = (id) => {
        updateWhisperWeightTypeStatus((old_status) =>
            old_status.data.map((item) =>
                id === item.id
                    ? { ...item, is_pending: true }
                    : item
            )
        );
    };
    const downloadedWhisperWeightType = (id) => {
        updateWhisperWeightTypeStatus((old_status) =>
            old_status.data.map((item) =>
                id === item.id
                    ? { ...item, is_downloaded: true, is_pending: false, progress: null }
                    : item
            )
        );
    };

    const downloadWhisperWeight = (weight_type) => {
        asyncStdoutToPython("/run/download_whisper_weight", weight_type);
    };

    return {
        currentWhisperWeightTypeStatus,
        updateWhisperWeightTypeStatus,

        updateDownloadedWhisperWeightTypeStatus,
        updateDownloadProgressWhisperWeightTypeStatus,
        pendingWhisperWeightType,
        downloadedWhisperWeightType,
        downloadWhisperWeight,
    };
};