import { useEffect } from "react";
import { useHotkeys } from "@logics_configs";
import { useIsBackendReady, useIsSoftwareUpdating, useIsVrctAvailable } from "@logics_common";

export const GlobalHotKeyController = () => {
    const { currentIsBackendReady } = useIsBackendReady();
    const { currentIsSoftwareUpdating } = useIsSoftwareUpdating();
    const { registerShortcuts, unregisterAll } = useHotkeys();

    const { currentIsVrctAvailable } = useIsVrctAvailable();

    useEffect(() => {
        const is_backend_ready = currentIsBackendReady.data;
        const is_software_updating = currentIsSoftwareUpdating.data;
        const is_vrct_available = currentIsVrctAvailable.data;

        if (is_vrct_available && is_backend_ready && !is_software_updating) {
            registerShortcuts();
        } else {
            unregisterAll();
        }
    }, [currentIsBackendReady.data, currentIsSoftwareUpdating.data, currentIsVrctAvailable.data]);

    return null;
};