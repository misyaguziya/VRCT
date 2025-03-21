import { useStore_OscIpAddress } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";
import { useNotificationStatus } from "@logics_common";

export const useOscIpAddress = () => {
    const { showNotification_Error } = useNotificationStatus();
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

    const saveErrorOscIpAddress = ({data, message, _result}) => {
        updateOscIpAddress(d => d.data);
        showNotification_Error(_result);
    };

    return {
        currentOscIpAddress,
        getOscIpAddress,
        updateOscIpAddress,
        setOscIpAddress,

        saveErrorOscIpAddress,
    };
};