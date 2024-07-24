import { Command } from "@tauri-apps/api/shell";
import { store } from "@store";

import { useMainFunction } from "./useMainFunction";

export const useStartPython = () => {
    const {
        updateState_Translation,
        updateState_TranscriptionSend,
        updateState_TranscriptionReceive,
    } = useMainFunction();

    const routes = {
        "/controller/callback_toggle_translation": updateState_Translation,
        "/controller/callback_toggle_transcription_send": updateState_TranscriptionSend,
        "/controller/callback_toggle_transcription_receive": updateState_TranscriptionReceive,
    };

    const receiveRoutes = (parsed_data) => {
        if (parsed_data.status === "ok") {
            const route = routes[parsed_data.id];
            if (route) {
                route({ data: parsed_data.data });
            } else {
                console.error(`Invalid path: ${parsed_data.id}`);
            }
        } else {
            console.log("Received data status is not 'ok'.", parsed_data);
        }
    };


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