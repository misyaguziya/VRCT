import { useStore_MicHostList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicHostList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicHostList, updateMicHostList } = useStore_MicHostList();

    const getMicHostList = () => {
        updateMicHostList(() => new Promise(() => {}));
        asyncStdoutToPython("/get/list_mic_host");
    };

    return {
        currentMicHostList,
        getMicHostList,
        updateMicHostList,
    };
};