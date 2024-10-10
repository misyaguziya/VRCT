import { useStore_Transparency } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useTransparency = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentTransparency, updateTransparency, pendingTransparency } = useStore_Transparency();

    const getTransparency = () => {
        pendingTransparency();
        asyncStdoutToPython("/get/data/transparency");
    };

    const setTransparency = (selected_transparency) => {
        pendingTransparency();
        asyncStdoutToPython("/set/data/transparency", selected_transparency);
    };

    return {
        currentTransparency,
        getTransparency,
        updateTransparency,
        setTransparency,
    };
};