import { useStore_SelectedMicDevice } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useSelectedMicDevice = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedMicDevice, updateSelectedMicDevice, pendingSelectedMicDevice } = useStore_SelectedMicDevice();

    const getSelectedMicDevice = () => {
        pendingSelectedMicDevice();
        asyncStdoutToPython("/get/data/selected_mic_device");
    };

    const setSelectedMicDevice = (selected_mic_device) => {
        pendingSelectedMicDevice();
        asyncStdoutToPython("/set/data/selected_mic_device", selected_mic_device);
    };

    return {
        currentSelectedMicDevice,
        getSelectedMicDevice,
        updateSelectedMicDevice,
        setSelectedMicDevice,
    };
};