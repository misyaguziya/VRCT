import { useStore_ComputeMode, useStore_InstalledEdition } from "@store";

export const useComputeMode = () => {
    const { currentComputeMode, updateComputeMode } = useStore_ComputeMode();
    const { currentInstalledEdition, updateInstalledEdition } = useStore_InstalledEdition();

    return {
        currentComputeMode,
        updateComputeMode,
        currentInstalledEdition,
        updateInstalledEdition,
    };
};