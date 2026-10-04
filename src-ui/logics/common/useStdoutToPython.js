import { store } from "@store";
import { encode } from "js-base64";
import { emit } from "@tauri-apps/api/event";
import { isLanguageMutation, beginLanguageMutation, createLanguageRequestId, getLanguageSnapshot,
    failLanguageMutationBeforeSend, failLanguageRead, languageMutationWriteUnconfirmed } from "../main/languageMutations";

export const useStdoutToPython = () => {
    const asyncStdoutToPython = async (path, value = undefined, languageRequest = undefined) => {
        const is_language_write = isLanguageMutation(path);
        const request = is_language_write ? { ...languageRequest, endpoint: path,
            requestId: languageRequest?.requestId ?? createLanguageRequestId(),
            source: languageRequest?.source ?? (store.is_vr_panel ? "vr" : "pc"),
            expectedSnapshot: languageRequest?.expectedSnapshot ?? getLanguageSnapshot() } : undefined;
        // VRパネルはsidecarを持たないため、メインウィンドウに送信を頼む (VrPanelSyncController)
        if (store.is_vr_panel) {
            await emit("vr-panel-stdout", { path, value, languageRequest: request });
            return;
        }

        if (is_language_write && !beginLanguageMutation(request)) return false;

        const send_object = { endpoint: path };
        if (value !== undefined) send_object.data = encode(JSON.stringify(value));

        // send to python
        const backend_subprocess = store.backend_subprocess;
        if (backend_subprocess) {
            return await backend_subprocess.write(JSON.stringify(send_object) + "\n").then(() => {
                return true;
            }).catch((err) => {
                console.log(err);
                if (is_language_write) languageMutationWriteUnconfirmed(request.requestId);
                else failLanguageRead(path);
                return false;
            });
        } else {
            console.error("Backend subprocess is not found.", backend_subprocess);
            if (is_language_write) failLanguageMutationBeforeSend(request.requestId);
            else failLanguageRead(path);
            return false;
        }
    };
    return { asyncStdoutToPython };
};
