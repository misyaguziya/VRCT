import { useStore_SelectedSpeakerDevice } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useSelectedSpeakerDevice = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedSpeakerDevice, updateSelectedSpeakerDevice, pendingSelectedSpeakerDevice } = useStore_SelectedSpeakerDevice();

    const getSelectedSpeakerDevice = () => {
        pendingSelectedSpeakerDevice();
        asyncStdoutToPython("/get/data/selected_speaker_device");
    };

    const setSelectedSpeakerDevice = (selected_speaker_device) => {
        pendingSelectedSpeakerDevice();
        asyncStdoutToPython("/set/data/selected_speaker_device", selected_speaker_device);
    };

    return {
        currentSelectedSpeakerDevice,
        getSelectedSpeakerDevice,
        updateSelectedSpeakerDevice,
        setSelectedSpeakerDevice,
    };
};