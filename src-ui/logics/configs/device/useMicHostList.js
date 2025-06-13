import { useStore_MicHostList } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { arrayToObject } from "@utils";

export const useMicHostList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicHostList, updateMicHostList, pendingMicHostList } = useStore_MicHostList();

    const getMicHostList = () => {
        pendingMicHostList();
        asyncStdoutToPython("/get/data/mic_host_list");
    };

    const updateMicHostList_FromBackend = (payload) => {
        updateMicHostList(arrayToObject(payload));
    };

    return {
        currentMicHostList,
        getMicHostList,
        updateMicHostList,

        updateMicHostList_FromBackend,
    };
};