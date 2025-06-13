import { useStore_MicDeviceList } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { arrayToObject } from "@utils";

export const useMicDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicDeviceList, updateMicDeviceList, pendingMicDeviceList } = useStore_MicDeviceList();

    const getMicDeviceList = () => {
        pendingMicDeviceList();
        asyncStdoutToPython("/get/data/mic_device_list");
    };


    const updateMicDeviceList_FromBackend = (payload) => {
        updateMicDeviceList(arrayToObject(payload));
    };


    return {
        currentMicDeviceList,
        getMicDeviceList,
        updateMicDeviceList,

        updateMicDeviceList_FromBackend,
    };
};