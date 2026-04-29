import { useStore_IsBackendReady } from "@store";

export const useIsBackendReady = () => {
    const { currentIsBackendReady, updateIsBackendReady } = useStore_IsBackendReady();

    const setIsBackendReady = (is_ready) => {
        updateIsBackendReady(is_ready);
    };

    return {
        currentIsBackendReady,
        setIsBackendReady,
        updateIsBackendReady,
    };
};