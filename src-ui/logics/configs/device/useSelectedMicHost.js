import { useStore_SelectedMicHost } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useSelectedMicHost = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedMicHost, updateSelectedMicHost, pendingSelectedMicHost } = useStore_SelectedMicHost();

    const getSelectedMicHost = () => {
        pendingSelectedMicHost();
        asyncStdoutToPython("/get/data/selected_mic_host");
    };

    const setSelectedMicHost = (selected_mic_host) => {
        pendingSelectedMicHost();
        asyncStdoutToPython("/set/data/selected_mic_host", selected_mic_host);
    };

    return {
        currentSelectedMicHost,
        getSelectedMicHost,
        updateSelectedMicHost,
        setSelectedMicHost,
    };
};