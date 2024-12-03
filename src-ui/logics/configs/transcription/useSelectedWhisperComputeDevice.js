import { useStore_SelectedWhisperComputeDevice } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectedWhisperComputeDevice = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedWhisperComputeDevice, updateSelectedWhisperComputeDevice, pendingSelectedWhisperComputeDevice } = useStore_SelectedWhisperComputeDevice();

    const getSelectedWhisperComputeDevice = () => {
        pendingSelectedWhisperComputeDevice();
        asyncStdoutToPython("/get/data/selected_transcription_compute_device");
    };

    const setSelectedWhisperComputeDevice = (selected_transcription_compute_device) => {
        pendingSelectedWhisperComputeDevice();
        asyncStdoutToPython("/set/data/selected_transcription_compute_device", selected_transcription_compute_device);
    };

    return {
        currentSelectedWhisperComputeDevice,
        getSelectedWhisperComputeDevice,
        updateSelectedWhisperComputeDevice,
        setSelectedWhisperComputeDevice,
    };
};