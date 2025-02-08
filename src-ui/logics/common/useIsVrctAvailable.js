import { useStore_IsVrctAvailable } from "@store";

export const useIsVrctAvailable = () => {
    const { currentIsVrctAvailable, updateIsVrctAvailable } = useStore_IsVrctAvailable();

    return {
        currentIsVrctAvailable,
        updateIsVrctAvailable,
    };
};