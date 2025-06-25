import { useEffect } from "react";
import { useAppearance } from "@logics_configs";

export const TransparencyController = () => {
    const { currentTransparency } = useAppearance();
    useEffect(() => {
        document.documentElement.style.setProperty("opacity", `${currentTransparency.data / 100}`);
    }, [currentTransparency.data]);

    return null;
};