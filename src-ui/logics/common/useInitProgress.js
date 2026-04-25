import { useStore_InitProgress } from "@store";

export const useInitProgress = () => {
    const { currentInitProgress, updateInitProgress } = useStore_InitProgress();

    return {
        currentInitProgress,
        updateInitProgress,
    };
};