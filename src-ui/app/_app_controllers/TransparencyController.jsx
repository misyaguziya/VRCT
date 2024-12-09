import { useEffect } from "react";
import { useTransparency } from "@logics_configs";

export const TransparencyController = () => {
    const { currentTransparency } = useTransparency();
    useEffect(() => {
        document.documentElement.style.setProperty("opacity", `${currentTransparency.data / 100}`);
    }, [currentTransparency.data]);

    return null;
};