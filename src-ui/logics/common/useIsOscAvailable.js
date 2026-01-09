import { useStore_IsOscAvailable } from "@store";

export const useIsOscAvailable = () => {
    const { currentIsOscAvailable, updateIsOscAvailable } = useStore_IsOscAvailable();

    return {
        currentIsOscAvailable,
        updateIsOscAvailable,
    };
};