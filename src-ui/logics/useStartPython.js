import { Command } from "@tauri-apps/api/shell";
import { store } from "@store";
import { useReceiveRoutes } from "./useReceiveRoutes";
export const useStartPython = () => {
    const { receiveRoutes } = useReceiveRoutes();

    const asyncStartPython = async () => {
        const command = Command.sidecar("bin/test");
        command.on("error", error => console.error(`error: "${error}"`));
        command.stdout.on("data", (line) => {
            let parsed_data = "";
            try {
                parsed_data = JSON.parse(line);
            } catch (error) {
                console.log(error);
                parsed_data = line;
            }
            console.log("from python:", parsed_data);
            receiveRoutes(parsed_data);
        });
        command.stderr.on("data", line => console.error("stderr:", line));
        const backend_subprocess = await command.spawn();
        store.backend_subprocess = backend_subprocess;
    };

    return { asyncStartPython };
};