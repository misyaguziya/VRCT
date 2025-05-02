import { Command } from "@tauri-apps/plugin-shell";
import { store } from "@store";
import { useReceiveRoutes } from "./useReceiveRoutes";
import {
    useNotificationStatus,
} from "@logics_common";

export const useStartPython = () => {
    const { receiveRoutes } = useReceiveRoutes();
    const { showNotification_Success, showNotification_Error } = useNotificationStatus();

    const asyncStartPython = async () => {
        const command = Command.sidecar("bin/VRCT-sidecar");
        command.on("error", error => console.error(`error: "${error}"`));
        command.stdout.on("data", (line) => {
            let parsed_data = "";
            try {
                parsed_data = JSON.parse(line);
                receiveRoutes(parsed_data);
            } catch (error) {
                console.log(error, line);
            }
        });
        command.stderr.on("data", line => {
            showNotification_Error(
                `An error occurred. Please restart VRCT or contact the developers. The last line:${JSON.stringify(line)}`, { hide_duration: null });
            console.error("stderr", line)
        });
        const backend_subprocess = await command.spawn();
        store.backend_subprocess = backend_subprocess;
    };

    return { asyncStartPython };
};