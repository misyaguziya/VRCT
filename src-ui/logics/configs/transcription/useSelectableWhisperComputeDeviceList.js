import { useStore_SelectableWhisperComputeDeviceList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectableWhisperComputeDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectableWhisperComputeDeviceList, updateSelectableWhisperComputeDeviceList, pendingSelectableWhisperComputeDeviceList } = useStore_SelectableWhisperComputeDeviceList();

    const getSelectableWhisperComputeDeviceList = () => {
        pendingSelectableWhisperComputeDeviceList();
        asyncStdoutToPython("/get/data/transcription_compute_device_list");
    };

    return {
        currentSelectableWhisperComputeDeviceList,
        getSelectableWhisperComputeDeviceList,
        updateSelectableWhisperComputeDeviceList,
    };
};