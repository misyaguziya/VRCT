import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useOpenFolder = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const openFolder_MessageLogs = () => {
        asyncStdoutToPython("/run/open_filepath_logs");
    };

    const openFolder_ConfigFile = () => {
        asyncStdoutToPython("/run/open_filepath_config_file");
    };

    return {
        openFolder_MessageLogs,
        openFolder_ConfigFile,
    };
};