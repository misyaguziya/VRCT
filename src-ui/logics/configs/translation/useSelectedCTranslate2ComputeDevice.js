import { useStore_SelectedCTranslate2ComputeDevice } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectedCTranslate2ComputeDevice = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedCTranslate2ComputeDevice, updateSelectedCTranslate2ComputeDevice, pendingSelectedCTranslate2ComputeDevice } = useStore_SelectedCTranslate2ComputeDevice();

    const getSelectedCTranslate2ComputeDevice = () => {
        pendingSelectedCTranslate2ComputeDevice();
        asyncStdoutToPython("/get/data/selected_translation_compute_device");
    };

    const setSelectedCTranslate2ComputeDevice = (selected_translation_compute_device) => {
        pendingSelectedCTranslate2ComputeDevice();
        asyncStdoutToPython("/set/data/selected_translation_compute_device", selected_translation_compute_device);
    };

    return {
        currentSelectedCTranslate2ComputeDevice,
        getSelectedCTranslate2ComputeDevice,
        updateSelectedCTranslate2ComputeDevice,
        setSelectedCTranslate2ComputeDevice,
    };
};