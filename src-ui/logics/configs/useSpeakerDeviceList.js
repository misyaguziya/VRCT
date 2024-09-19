import { useStore_SpeakerDeviceList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSpeakerDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSpeakerDeviceList, updateSpeakerDeviceList } = useStore_SpeakerDeviceList();

    const getSpeakerDeviceList = () => {
        updateSpeakerDeviceList(() => new Promise(() => {}));
        asyncStdoutToPython("/get/list_speaker_device");
    };

    return {
        currentSpeakerDeviceList,
        getSpeakerDeviceList,
        updateSpeakerDeviceList,
    };
};