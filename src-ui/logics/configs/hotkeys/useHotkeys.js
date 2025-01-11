import { useStore_Hotkeys } from "@store";
// import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useHotkeys = () => {
    // const { asyncStdoutToPython } = useStdoutToPython();
    const { currentHotkeys, updateHotkeys, pendingHotkeys } = useStore_Hotkeys();

    const getHotkeys = () => {
        // pendingHotkeys();
        // asyncStdoutToPython("/get/data/osc_ip_address");
    };

    const setHotkeys = (hotkeys) => {
        updateHotkeys(hotkeys);
        // pendingHotkeys();
        // asyncStdoutToPython("/set/data/osc_ip_address", osc_ip_address);
    };

    return {
        currentHotkeys,
        // getHotkeys,
        updateHotkeys,
        setHotkeys,
    };
};