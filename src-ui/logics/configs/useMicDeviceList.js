import { useMicDeviceList as useStoreMicDeviceList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicDeviceList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicDeviceList, updateMicDeviceList } = useStoreMicDeviceList();

    const getMicDeviceList = () => {
        updateMicDeviceList(() => new Promise(() => {}));
        asyncStdoutToPython("/controller/list_mic_device");
    };

    return { currentMicDeviceList, getMicDeviceList, updateMicDeviceList };
};