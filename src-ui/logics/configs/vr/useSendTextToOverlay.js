import { useStdoutToPython } from "@useStdoutToPython";

export const useSendTextToOverlay = () => {
    const { asyncStdoutToPython } = useStdoutToPython();

    const sendTextToOverlay = (text) => {
        asyncStdoutToPython("/run/send_text_overlay", text);
    };

    return {
        sendTextToOverlay,
    };
};