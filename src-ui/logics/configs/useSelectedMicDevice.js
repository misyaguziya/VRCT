import { useStore_SelectedMicDevice } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectedMicDevice = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedMicDevice, updateSelectedMicDevice, pendingSelectedMicDevice } = useStore_SelectedMicDevice();

    const getSelectedMicDevice = () => {
        pendingSelectedMicDevice();
        asyncStdoutToPython("/get/selected_mic_device");
    };

    const setSelectedMicDevice = (selected_mic_device) => {
        pendingSelectedMicDevice();
        asyncStdoutToPython("/set/selected_mic_device", selected_mic_device);
    };

    return {
        currentSelectedMicDevice,
        getSelectedMicDevice,
        updateSelectedMicDevice,
        setSelectedMicDevice,
    };
};