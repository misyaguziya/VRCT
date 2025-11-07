import { useEffect } from "react";
import { useAppearance } from "@logics_configs";

export const FontFamilyController = () => {
    const { currentSelectedFontFamily } = useAppearance();
    useEffect(() => {
        document.documentElement.style.setProperty("--font_family", currentSelectedFontFamily.data);
    }, [currentSelectedFontFamily.data]);

    return null;
};
