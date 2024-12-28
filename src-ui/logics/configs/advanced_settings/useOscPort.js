import { useStore_OscPort } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useOscPort = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentOscPort, updateOscPort, pendingOscPort } = useStore_OscPort();

    const getOscPort = () => {
        pendingOscPort();
        asyncStdoutToPython("/get/data/osc_port");
    };

    const setOscPort = (osc_port) => {
        pendingOscPort();
        asyncStdoutToPython("/set/data/osc_port", osc_port);
    };

    return {
        currentOscPort,
        getOscPort,
        updateOscPort,
        setOscPort,
    };
};