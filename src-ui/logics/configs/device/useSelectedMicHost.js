import { useStore_SelectedMicHost } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useSelectedMicDevice } from "@logics_configs";

export const useSelectedMicHost = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedMicHost, updateSelectedMicHost, pendingSelectedMicHost } = useStore_SelectedMicHost();

    const { updateSelectedMicDevice } = useSelectedMicDevice();

    const getSelectedMicHost = () => {
        pendingSelectedMicHost();
        asyncStdoutToPython("/get/data/selected_mic_host");
    };

    const setSelectedMicHost = (selected_mic_host) => {
        pendingSelectedMicHost();
        asyncStdoutToPython("/set/data/selected_mic_host", selected_mic_host);
    };


    // Need refactoring (Duplicated, Host, Device)
    const updateSelectedMicHostAndDevice = (payload) => {
        updateSelectedMicHost(payload.host);
        updateSelectedMicDevice(payload.device);
    };


    return {
        currentSelectedMicHost,
        getSelectedMicHost,
        updateSelectedMicHost,
        setSelectedMicHost,

        updateSelectedMicHostAndDevice,
    };
};