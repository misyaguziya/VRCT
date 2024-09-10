import { useMicHostList as useStoreMicHostList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicHostList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicHostList, updateMicHostList } = useStoreMicHostList();

    const getMicHostList = () => {
        updateMicHostList(() => new Promise(() => {}));
        asyncStdoutToPython("/controller/list_mic_host");
    };

    return { currentMicHostList, getMicHostList, updateMicHostList };
};