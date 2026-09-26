import { store } from "@store";
import { encode } from "js-base64";
import { emit } from "@tauri-apps/api/event";

export const useStdoutToPython = () => {
    const asyncStdoutToPython = async (path, value = undefined) => {
        // VRパネルはsidecarを持たないため、メインウィンドウに送信を頼む (VrPanelSyncController)
        if (store.is_vr_panel) {
            await emit("vr-panel-stdout", { path, value });
            return;
        }

        let send_object = { endpoint: path };
        if (value !== undefined) send_object.data = encode(JSON.stringify(value));

        // send to python
        const backend_subprocess = store.backend_subprocess;
        if (backend_subprocess) {
            await backend_subprocess.write(JSON.stringify(send_object) + "\n").then(() => {
            }).catch((err) => {
                console.log(err);
            });
        } else {
            console.error("Backend subprocess is not found.", backend_subprocess);
        }
    };
    return { asyncStdoutToPython };
};