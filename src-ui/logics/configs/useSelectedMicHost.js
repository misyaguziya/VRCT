import { useStore_SelectedMicHost } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectedMicHost = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedMicHost, updateSelectedMicHost } = useStore_SelectedMicHost();

    const getSelectedMicHost = () => {
        updateSelectedMicHost(() => new Promise(() => {}));
        asyncStdoutToPython("/config/choice_mic_host");
    };

    const setSelectedMicHost = (selected_mic_host) => {
        updateSelectedMicHost(() => new Promise(() => {}));
        asyncStdoutToPython("/controller/callback_set_mic_host", selected_mic_host);
    };

    return {
        currentSelectedMicHost,
        getSelectedMicHost,
        updateSelectedMicHost,
        setSelectedMicHost,
    };
};