import { useStore_EnableAutoExportMessageLogs } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoExportMessageLogs = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoExportMessageLogs, updateEnableAutoExportMessageLogs, pendingEnableAutoExportMessageLogs } = useStore_EnableAutoExportMessageLogs();

    const getEnableAutoExportMessageLogs = () => {
        pendingEnableAutoExportMessageLogs();
        asyncStdoutToPython("/get/data/logger_feature");
    };

    const toggleEnableAutoExportMessageLogs = () => {
        pendingEnableAutoExportMessageLogs();
        if (currentEnableAutoExportMessageLogs.data) {
            asyncStdoutToPython("/set/disable/logger_feature");
        } else {
            asyncStdoutToPython("/set/enable/logger_feature");
        }
    };

    return {
        currentEnableAutoExportMessageLogs,
        getEnableAutoExportMessageLogs,
        toggleEnableAutoExportMessageLogs,
        updateEnableAutoExportMessageLogs,
    };
};