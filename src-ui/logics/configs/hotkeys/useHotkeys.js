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
        const send_obj = {
            ...currentHotkeys.data,
            ...hotkeys,
        };
        asyncStdoutToPython("/set/data/hotkeys", send_obj);


    };

    return {
        currentHotkeys,
        getHotkeys,
        updateHotkeys,
        setHotkeys,
    };
};