import { useStore_SelectedSpeakerDevice } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectedSpeakerDevice = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedSpeakerDevice, updateSelectedSpeakerDevice } = useStore_SelectedSpeakerDevice();

    const getSelectedSpeakerDevice = () => {
        updateSelectedSpeakerDevice(() => new Promise(() => {}));
        asyncStdoutToPython("/get/selected_speaker_device");
    };

    const setSelectedSpeakerDevice = (selected_speaker_device) => {
        updateSelectedSpeakerDevice(() => new Promise(() => {}));
        asyncStdoutToPython("/set/selected_speaker_device", selected_speaker_device);
    };

    return {
        currentSelectedSpeakerDevice,
        getSelectedSpeakerDevice,
        updateSelectedSpeakerDevice,
        setSelectedSpeakerDevice,
    };
};