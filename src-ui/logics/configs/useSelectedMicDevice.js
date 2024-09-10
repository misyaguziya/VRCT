import { useSelectedMicDevice as useStoreSelectedMicDevice } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectedMicDevice = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedMicDevice, updateSelectedMicDevice } = useStoreSelectedMicDevice();

    const getSelectedMicDevice = () => {
        updateSelectedMicDevice(() => new Promise(() => {}));
        asyncStdoutToPython("/config/choice_mic_device");
    };

    const setSelectedMicDevice = (selected_mic_device) => {
        updateSelectedMicDevice(() => new Promise(() => {}));
        asyncStdoutToPython("/controller/callback_set_mic_device", selected_mic_device);
    };

    return { currentSelectedMicDevice, getSelectedMicDevice, updateSelectedMicDevice, setSelectedMicDevice };
};