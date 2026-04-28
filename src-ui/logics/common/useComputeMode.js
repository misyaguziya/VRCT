import { useStore_ComputeMode } from "@store";

export const useComputeMode = () => {
    const { currentComputeMode, updateComputeMode } = useStore_ComputeMode();

    return {
        currentComputeMode,
        updateComputeMode,
    };
};