import { useEffect } from "react";
import { useSelectedFontFamily } from "@logics_configs";

export const FontFamilyController = () => {
    const { currentSelectedFontFamily } = useSelectedFontFamily();
    useEffect(() => {
        document.documentElement.style.setProperty("--font_family", currentSelectedFontFamily.data);
    }, [currentSelectedFontFamily.data]);

    return null;
};
