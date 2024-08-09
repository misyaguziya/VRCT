import { getCurrent } from "@tauri-apps/api/window";
import { useEffect, useRef } from "react";
import { useStartPython } from "@logics/useStartPython";
import { useConfig } from "@logics/useConfig";

import { MainPage } from "./main_page/MainPage";
import { ConfigPage } from "./config_page/ConfigPage";


export const App = () => {
    const { asyncStartPython } = useStartPython();
    const hasRunRef = useRef(false);
    const main_page = getCurrent();

    const { getSoftwareVersion } = useConfig();

    useEffect(() => {
        main_page.setDecorations(true);
        if (!hasRunRef.current) {
            asyncStartPython().then((result) => {
                getSoftwareVersion();
            }).catch((err) => {

            });
        }
        return () => hasRunRef.current = true;
    }, []);

    return (
        <>
            <MainPage/>
            <ConfigPage/>
        </>
    );
};