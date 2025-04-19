import React from "react";
import clsx from "clsx";

if (typeof window !== "undefined") {
    window.React = React;
    window.clsx = clsx;
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