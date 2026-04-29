import { useStore_IsSoftwareUpdating } from "@store";

export const useIsSoftwareUpdating = () => {
    const { currentIsSoftwareUpdating, updateIsSoftwareUpdating } = useStore_IsSoftwareUpdating();

    return {
        currentIsSoftwareUpdating,
        updateIsSoftwareUpdating,
    };
};