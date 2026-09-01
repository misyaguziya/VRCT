import { useStore_AvailableReleases } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useAvailableReleases = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentAvailableReleases, updateAvailableReleases, pendingAvailableReleases } = useStore_AvailableReleases();

    const getAvailableReleases = () => {
        pendingAvailableReleases();
        asyncStdoutToPython("/get/data/available_releases");
    };

    const updateAvailableReleasesFromBackend = (payload) => {
        updateAvailableReleases(Array.isArray(payload) ? payload : []);
    };

    return {
        currentAvailableReleases,
        getAvailableReleases,
        updateAvailableReleasesFromBackend,
    };
};
