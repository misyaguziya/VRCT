import React from "react";
import clsx from "clsx";
import * as reactI18next from "react-i18next";

if (typeof window !== "undefined") {
    window.React = React;
    window.clsx = clsx;
    window.reactI18next = reactI18next;
}

import { LoadPluginsController } from "./plugins_controllers/LoadPluginsController";
import { FetchLatestPluginsDataController } from "./plugins_controllers/FetchLatestPluginsDataController";
import { MergePluginsController } from "./plugins_controllers/MergePluginsController";

export const PluginsController = () => {

    return (
        <>
            <MergePluginsController />
            <LoadPluginsController />
            <FetchLatestPluginsDataController />
        </>
    );
};