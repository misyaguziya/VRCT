import { useSpeakerDeviceList as useStoreSpeakerDeviceList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSpeakerDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSpeakerDeviceList, updateSpeakerDeviceList } = useStoreSpeakerDeviceList();

    const getSpeakerDeviceList = () => {
        updateSpeakerDeviceList(() => new Promise(() => {}));
        asyncStdoutToPython("/controller/list_speaker_device");
    };

    return { currentSpeakerDeviceList, getSpeakerDeviceList, updateSpeakerDeviceList };
};