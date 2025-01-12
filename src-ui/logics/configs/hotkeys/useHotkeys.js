import { useStore_Hotkeys } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useHotkeys = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentHotkeys, updateHotkeys, pendingHotkeys } = useStore_Hotkeys();

    const getHotkeys = () => {
        pendingHotkeys();
        asyncStdoutToPython("/get/data/hotkeys");
    };

    const setHotkeys = (hotkeys) => {
        pendingHotkeys();
        asyncStdoutToPython("/set/data/hotkeys", hotkeys);
    };

    return {
        currentHotkeys,
        getHotkeys,
        updateHotkeys,
        setHotkeys,
    };
};