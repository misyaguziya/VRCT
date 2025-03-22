import { useStore_OscIpAddress } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useOscIpAddress = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentOscIpAddress, updateOscIpAddress, pendingOscIpAddress } = useStore_OscIpAddress();

    const getOscIpAddress = () => {
        pendingOscIpAddress();
        asyncStdoutToPython("/get/data/osc_ip_address");
    };

    const setOscIpAddress = (osc_ip_address) => {
        pendingOscIpAddress();
        asyncStdoutToPython("/set/data/osc_ip_address", osc_ip_address);
    };

    return {
        currentOscIpAddress,
        getOscIpAddress,
        updateOscIpAddress,
        setOscIpAddress,
    };
};