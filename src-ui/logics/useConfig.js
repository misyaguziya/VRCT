import {
    useSoftwareVersion,
    useMicHostList,
    useSelectedMicHost,
    useMicDeviceList,
    useSelectedMicDevice,
} from "@store";

import { useStdoutToPython } from "./useStdoutToPython";

import { arrayToObject } from "@utils/arrayToObject";

export const useConfig = () => {
    const { asyncStdoutToPython } = useStdoutToPython();

    const { updateSoftwareVersion } = useSoftwareVersion();
    const { updateMicHostList } = useMicHostList();
    const { updateSelectedMicHost } = useSelectedMicHost();
    const { updateMicDeviceList } = useMicDeviceList();
    const { updateSelectedMicDevice } = useSelectedMicDevice();


    return {
        getSoftwareVersion: () => asyncStdoutToPython("/config/version"),
        updateSoftwareVersion: (payload) => updateSoftwareVersion(payload.data),

        getMicHostList: () => asyncStdoutToPython("/controller/list_mic_host"),
        updateMicHostList: (payload) => {
            updateMicHostList(arrayToObject(payload.data));
        },
        getSelectedMicHost: () => asyncStdoutToPython("/config/choice_mic_host"),
        updateSelectedMicHost: (payload) => {
            updateSelectedMicHost(payload.data);
        },

        getMicDeviceList: () => asyncStdoutToPython("/controller/list_mic_device"),
        updateMicDeviceList: (payload) => {
            updateMicDeviceList(arrayToObject(payload.data));
        },
        getSelectedMicDevice: () => asyncStdoutToPython("/config/choice_mic_device"),
        updateSelectedMicDevice: (payload) => {
            updateSelectedMicDevice(payload.data);
        },


    };
};