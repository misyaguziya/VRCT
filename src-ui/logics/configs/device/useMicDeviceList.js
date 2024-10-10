import { useStore_MicDeviceList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicDeviceList, updateMicDeviceList, pendingMicDeviceList } = useStore_MicDeviceList();

    const getMicDeviceList = () => {
        pendingMicDeviceList();
        asyncStdoutToPython("/get/data/mic_device_list");
    };

    return {
        currentMicDeviceList,
        getMicDeviceList,
        updateMicDeviceList,
    };
};