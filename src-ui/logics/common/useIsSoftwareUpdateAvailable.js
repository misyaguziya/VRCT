import { useStore_IsSoftwareUpdateAvailable } from "@store";

export const useIsSoftwareUpdateAvailable = () => {
    const { currentIsSoftwareUpdateAvailable, updateIsSoftwareUpdateAvailable } = useStore_IsSoftwareUpdateAvailable();

    return {
        currentIsSoftwareUpdateAvailable,
        updateIsSoftwareUpdateAvailable,
    };
};