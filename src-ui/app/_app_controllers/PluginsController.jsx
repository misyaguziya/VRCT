import React from "react";
import clsx from "clsx";

if (typeof window !== "undefined") {
    window.React = React;
    window.clsx = clsx;
}

import { LoadPluginsController } from "./plugins_controllers/LoadPluginsController";
import { FetchLatestPluginsDataController } from "./plugins_controllers/FetchLatestPluginsDataController";
// import { MergeSavedPluginsStatusController } from "./plugins_controllers/MergeSavedPluginsStatusController";
import { MergePluginsController } from "./plugins_controllers/MergePluginsController";

export const PluginsController = ({ pluginsControllerHasRunRef }) => {

    return (
        <>
            <MergePluginsController />
            <LoadPluginsController pluginsControllerHasRunRef={pluginsControllerHasRunRef}/>
            <FetchLatestPluginsDataController pluginsControllerHasRunRef={pluginsControllerHasRunRef}/>
            {/* <MergeSavedPluginsStatusController /> */}
        </>
    );
};