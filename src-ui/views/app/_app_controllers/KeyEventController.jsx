import { useEffect } from "react";

export const KeyEventController = () => {
    useEffect(() => {
        const handleKeydown = (event) => {
            if (
                event.key === "F5" || // Page reload
                event.key === "F10" || // Focus thw window menu (maybe)
                event.key === "F12" || // Open dev tool
                (event.ctrlKey && event.key === "r") ||
                (event.metaKey && event.key === "r")
            ) {
                event.preventDefault();
            }
        };

        const handleContextmenu = (event) => {
            event.preventDefault();
        };

        document.addEventListener("keydown", handleKeydown);
        document.addEventListener("contextmenu", handleContextmenu);

        return () => {
            document.removeEventListener("keydown", handleKeydown);
            document.removeEventListener("contextmenu", handleContextmenu);
        };
    }, []);

    return null;
};
