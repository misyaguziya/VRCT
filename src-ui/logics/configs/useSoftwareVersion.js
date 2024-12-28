import { useStore_SoftwareVersion } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSoftwareVersion = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSoftwareVersion, updateSoftwareVersion, pendingSoftwareVersion } = useStore_SoftwareVersion();

    const getSoftwareVersion = () => {
        pendingSoftwareVersion();
        asyncStdoutToPython("/get/data/version");
    };

    return {
        currentSoftwareVersion,
        getSoftwareVersion,
        updateSoftwareVersion,
    };
};