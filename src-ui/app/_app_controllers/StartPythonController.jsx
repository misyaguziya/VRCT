import { invoke } from "@tauri-apps/api/core";
import { useEffect, useRef } from "react";
import { useStartPython } from "@logics/useStartPython";
import { useStdoutToPython } from "@logics/useStdoutToPython";

import { useStore_SelectableFontFamilyList } from "@store";
import { arrayToObject } from "@utils";

export const StartPythonController = () => {
    const { asyncStartPython } = useStartPython();
    const hasRunRef = useRef(false);
    const { asyncFetchFonts } = useAsyncFetchFonts();

    useEffect(() => {
        if (!hasRunRef.current) {
            asyncStartPython().then(() => {
                startFeedingToWatchDogController();
                asyncFetchFonts();
            }).catch((err) => {
                console.error(err);
            });
        }
        return () => hasRunRef.current = true;
    }, []);

    return null;
};

const useAsyncFetchFonts = () => {
    const { updateSelectableFontFamilyList } = useStore_SelectableFontFamilyList();
    const asyncFetchFonts = async () => {
        try {
            let fonts = await invoke("get_font_list");
            fonts = fonts.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
            updateSelectableFontFamilyList(arrayToObject(fonts));
        } catch (error) {
            console.error("Error fetching fonts:", error);
        }
    };
    return { asyncFetchFonts };
};

const startFeedingToWatchDogController = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    setInterval(() => {
        asyncStdoutToPython("/run/feed_watchdog");
    }, 20000); // 20000ミリ秒 = 20秒
};