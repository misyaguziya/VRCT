import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useOpenFolder = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const openFolder_MessageLogs = () => {
        asyncStdoutToPython("/run/open_filepath_logs");
    };

    return {
        openFolder_MessageLogs,
    };
};