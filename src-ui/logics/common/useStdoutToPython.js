import { store } from "@store";
import { encode } from "js-base64";

export const useStdoutToPython = () => {
    const asyncStdoutToPython = async (path, value = undefined) => {
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