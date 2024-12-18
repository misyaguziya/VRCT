import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSendTextToOverlay = () => {
    const { asyncStdoutToPython } = useStdoutToPython();

    const sendTextToOverlay = (text) => {
        asyncStdoutToPython("/run/send_text_overlay_small_log", text);
    };

    return {
        sendTextToOverlay,
    };
};