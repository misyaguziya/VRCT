import { useStore_MicDeviceList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicDeviceList, updateMicDeviceList } = useStore_MicDeviceList();

    const getMicDeviceList = () => {
        updateMicDeviceList(() => new Promise(() => {}));
        asyncStdoutToPython("/get/list_mic_device");
    };

    return {
        currentMicDeviceList,
        getMicDeviceList,
        updateMicDeviceList,
    };
};