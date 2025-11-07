import { useEffect } from "react";
import { useAppearance } from "@logics_configs";

export const UiSizeController = () => {
    const { currentUiScaling } = useAppearance();
    const font_size = 62.5 * currentUiScaling.data / 100;

    useEffect(() => {
        document.documentElement.style.setProperty("font-size", `${font_size}%`);
    }, [currentUiScaling.data]);

    return null;
};