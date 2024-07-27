import { store } from "@store";

export const useStdoutToPython = () => {
    const asyncStdoutToPython = async (value) => {
        // send to python
        const backend_subprocess = store.backend_subprocess;
        if (backend_subprocess) {
            await backend_subprocess.write(JSON.stringify(value) + "\n").then(() => {
            }).catch((err) => {
                console.log(err);
            });
        } else {
            console.error("Backend subprocess is not found.", backend_subprocess);
        }
    };
    return { asyncStdoutToPython };
};