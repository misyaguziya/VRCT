import { useSoftwareVersion as useStoreSoftwareVersion } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSoftwareVersion = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSoftwareVersion, updateSoftwareVersion } = useStoreSoftwareVersion();

    const getSoftwareVersion = () => {
        updateSoftwareVersion(() => new Promise(() => {}));
        asyncStdoutToPython("/config/version");
    };

    return { currentSoftwareVersion, getSoftwareVersion, updateSoftwareVersion };
};