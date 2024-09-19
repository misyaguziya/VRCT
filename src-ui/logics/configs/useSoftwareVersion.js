import { useStore_SoftwareVersion } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSoftwareVersion = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSoftwareVersion, updateSoftwareVersion } = useStore_SoftwareVersion();

    const getSoftwareVersion = () => {
        updateSoftwareVersion(() => new Promise(() => {}));
        asyncStdoutToPython("/get/version");
    };

    return {
        currentSoftwareVersion,
        getSoftwareVersion,
        updateSoftwareVersion,
    };
};