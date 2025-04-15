import React, { useEffect } from "react";
import { LoadPluginsController } from "./plugins_controllers/LoadPluginsController";
import { FetchLatestPluginsDataController } from "./plugins_controllers/FetchLatestPluginsDataController";
import { MergeSavedPluginsStatusController } from "./plugins_controllers/MergeSavedPluginsStatusController";

export const PluginsController = () => {

    return (
        <>
            <LoadPluginsController />
            <FetchLatestPluginsDataController />
            <MergeSavedPluginsStatusController />
        </>
    );
};