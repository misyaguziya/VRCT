import { useStdoutToPython } from "@useStdoutToPython";

export const useOpenFolder = () => {
    const { asyncStdoutToPython } = useStdoutToPython();

    const openFolder_MessageLogs = () => {
        asyncStdoutToPython("/run/open_filepath_logs");
    };
    const openedFolder_MessageLogs = () => {
        console.log("Opened Directory, Message Logs");
    };

    const openFolder_ConfigFile = () => {
        asyncStdoutToPython("/run/open_filepath_config_file");
    };
    const openedFolder_ConfigFile = () => {
        console.log("Opened Directory, Config File");
    };

    return {
        openFolder_MessageLogs,
        openFolder_ConfigFile,

        openedFolder_MessageLogs,
        openedFolder_ConfigFile,
    };
};