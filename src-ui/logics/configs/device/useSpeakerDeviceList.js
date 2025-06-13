import { useStore_SpeakerDeviceList } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { arrayToObject } from "@utils";

export const useSpeakerDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSpeakerDeviceList, updateSpeakerDeviceList, pendingSpeakerDeviceList } = useStore_SpeakerDeviceList();

    const getSpeakerDeviceList = () => {
        pendingSpeakerDeviceList();
        asyncStdoutToPython("/get/data/speaker_device_list");
    };

    const updateSpeakerDeviceList_FromBackend = (payload) => {
        updateSpeakerDeviceList(arrayToObject(payload));
    };


    return {
        currentSpeakerDeviceList,
        getSpeakerDeviceList,
        updateSpeakerDeviceList,

        updateSpeakerDeviceList_FromBackend,
    };
};