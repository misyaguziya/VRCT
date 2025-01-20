import { useEffect } from "react";
import { useHotkeys } from "@logics_configs";
import { useIsBackendReady, useIsSoftwareUpdating } from "@logics_common";

export const GlobalHotKeyController = () => {
    const { currentIsBackendReady } = useIsBackendReady();
    const { currentIsSoftwareUpdating } = useIsSoftwareUpdating();
    const { registerShortcuts, unregisterAll } = useHotkeys();

    useEffect(() => {
        const is_backend_ready = currentIsBackendReady.data;
        const is_software_updating = currentIsSoftwareUpdating.data;

        if (is_backend_ready && !is_software_updating) {
            registerShortcuts();
        } else if (is_software_updating) {
            unregisterAll();
        }
    }, [currentIsBackendReady.data, currentIsSoftwareUpdating.data]);

    return null;
};