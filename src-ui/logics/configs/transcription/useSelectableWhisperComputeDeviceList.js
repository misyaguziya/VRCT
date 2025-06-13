import { useStore_SelectableWhisperComputeDeviceList } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { transformToIndexedArray } from "@utils";

export const useSelectableWhisperComputeDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectableWhisperComputeDeviceList, updateSelectableWhisperComputeDeviceList, pendingSelectableWhisperComputeDeviceList } = useStore_SelectableWhisperComputeDeviceList();

    const getSelectableWhisperComputeDeviceList = () => {
        pendingSelectableWhisperComputeDeviceList();
        asyncStdoutToPython("/get/data/transcription_compute_device_list");
    };

    const updateSelectableWhisperComputeDeviceList_FromBackend = (payload) => {
        updateSelectableWhisperComputeDeviceList(transformToIndexedArray(payload));
    };

    return {
        currentSelectableWhisperComputeDeviceList,
        getSelectableWhisperComputeDeviceList,
        updateSelectableWhisperComputeDeviceList,

        updateSelectableWhisperComputeDeviceList_FromBackend,
    };
};