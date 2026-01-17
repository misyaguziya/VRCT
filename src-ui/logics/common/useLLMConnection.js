import { useStdoutToPython } from "@useStdoutToPython";
import {
    useStore_IsLMStudioConnected,
    useStore_IsOllamaConnected,
} from "@store";

export const useLLMConnection = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const {
        currentIsLMStudioConnected,
        updateIsLMStudioConnected,
        pendingIsLMStudioConnected,
    } = useStore_IsLMStudioConnected();
    const {
        currentIsOllamaConnected,
        updateIsOllamaConnected,
        pendingIsOllamaConnected,
    } = useStore_IsOllamaConnected();

    const checkConnection_LMStudio = () => {
        pendingIsLMStudioConnected();
        asyncStdoutToPython("/run/lmstudio_connection");
    };
    const setConnectionStatus_LMStudio = (is_connected) => {
        updateIsLMStudioConnected(is_connected);
    };

    const checkConnection_Ollama = () => {
        pendingIsOllamaConnected();
        asyncStdoutToPython("/run/ollama_connection");
    };
    const setConnectionStatus_Ollama = (is_connected) => {
        updateIsOllamaConnected(is_connected);
    };

    return {
        currentIsLMStudioConnected,
        updateIsLMStudioConnected,
        setConnectionStatus_LMStudio,
        checkConnection_LMStudio,

        currentIsOllamaConnected,
        updateIsOllamaConnected,
        setConnectionStatus_Ollama,
        checkConnection_Ollama,
    };
};