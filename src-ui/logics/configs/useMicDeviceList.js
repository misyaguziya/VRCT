import { useStore_MicDeviceList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicDeviceList, updateMicDeviceList, pendingMicDeviceList } = useStore_MicDeviceList();

    const getMicDeviceList = () => {
        pendingMicDeviceList();
        asyncStdoutToPython("/get/list_mic_device");
    };

    return {
        currentMicDeviceList,
        getMicDeviceList,
        updateMicDeviceList,
    };
};