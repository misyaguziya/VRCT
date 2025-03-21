import { useStore_OscPort } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";
import { useNotificationStatus } from "@logics_common";

export const useOscPort = () => {
    const { showNotification_Error } = useNotificationStatus();
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

    const saveErrorOscPort = ({data, message, _result}) => {
        updateOscPort(d => d.data);
        showNotification_Error(_result);
    };

    return {
        currentOscPort,
        getOscPort,
        updateOscPort,
        setOscPort,

        saveErrorOscPort,
    };
};