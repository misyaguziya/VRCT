import { useStore_MicHostList } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useMicHostList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicHostList, updateMicHostList, pendingMicHostList } = useStore_MicHostList();

    const getMicHostList = () => {
        pendingMicHostList();
        asyncStdoutToPython("/get/data/mic_host_list");
    };

    return {
        currentMicHostList,
        getMicHostList,
        updateMicHostList,
    };
};