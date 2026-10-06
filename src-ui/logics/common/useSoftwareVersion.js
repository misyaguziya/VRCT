import { useStore_SoftwareVersion, useStore_LatestSoftwareVersionInfo } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useSoftwareVersion = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentLatestSoftwareVersionInfo, updateLatestSoftwareVersionInfo } = useStore_LatestSoftwareVersionInfo();
    const { currentSoftwareVersion, updateSoftwareVersion, pendingSoftwareVersion } = useStore_SoftwareVersion();

    const getSoftwareVersion = () => {
        pendingSoftwareVersion();
        asyncStdoutToPython("/get/data/version");
    };

    const updateSoftwareVersionInfo = (payload) => {
        updateLatestSoftwareVersionInfo(prev => ({
            is_update_available: payload.is_update_available,
            new_version: payload.new_version || prev.data.new_version,
        }));
    };

    return {
        currentSoftwareVersion,
        getSoftwareVersion,
        updateSoftwareVersion,

        updateSoftwareVersionInfo,
        currentLatestSoftwareVersionInfo,
        updateLatestSoftwareVersionInfo,
    };
};