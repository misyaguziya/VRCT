import { useStore_SelectedMicHost } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectedMicHost = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedMicHost, updateSelectedMicHost } = useStore_SelectedMicHost();

    const getSelectedMicHost = () => {
        updateSelectedMicHost(() => new Promise(() => {}));
        asyncStdoutToPython("/get/selected_mic_host");
    };

    const setSelectedMicHost = (selected_mic_host) => {
        updateSelectedMicHost(() => new Promise(() => {}));
        asyncStdoutToPython("/set/selected_mic_host", selected_mic_host);
    };

    return {
        currentSelectedMicHost,
        getSelectedMicHost,
        updateSelectedMicHost,
        setSelectedMicHost,
    };
};