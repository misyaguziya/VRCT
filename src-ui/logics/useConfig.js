import {
    useSoftwareVersion,
    useMicHostList,
    useSelectedMicHost,
    useMicDeviceList,
    useSelectedMicDevice,
    useSpeakerDeviceList,
    useSelectedSpeakerDevice,
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
    const { updateSpeakerDeviceList } = useSpeakerDeviceList();
    const { updateSelectedSpeakerDevice } = useSelectedSpeakerDevice();


    const asyncPending = () => new Promise(() => {});
    return {
        getSoftwareVersion: () => {
            updateSoftwareVersion(asyncPending);
            asyncStdoutToPython("/config/version");
        },
        updateSoftwareVersion: (payload) => updateSoftwareVersion(payload.data),

        getMicHostList: () => {
            updateMicHostList(asyncPending);
            asyncStdoutToPython("/controller/list_mic_host");
        },
        updateMicHostList: (payload) => {
            updateMicHostList(arrayToObject(payload.data));
        },
        getSelectedMicHost: () => {
            updateSelectedMicHost(asyncPending);
            asyncStdoutToPython("/config/choice_mic_host");
        },
        updateSelectedMicHost: (payload) => {
            updateSelectedMicHost(payload.data);
        },
        setSelectedMicHost: (selected_mic_host) => {
            updateSelectedMicHost(asyncPending);
            asyncStdoutToPython("/controller/callback_set_mic_host", selected_mic_host);
        },

        getMicDeviceList: () => {
            updateMicDeviceList(asyncPending);
            asyncStdoutToPython("/controller/list_mic_device");
        },
        updateMicDeviceList: (payload) => {
            updateMicDeviceList(arrayToObject(payload.data));
        },
        getSelectedMicDevice: () => {
            updateSelectedMicDevice(asyncPending);
            asyncStdoutToPython("/config/choice_mic_device");
        },
        updateSelectedMicDevice: (payload) => {
            updateSelectedMicDevice(payload.data);
        },
        setSelectedMicDevice: (selected_mic_device) => {
            updateSelectedMicDevice(asyncPending);
            asyncStdoutToPython("/controller/callback_set_mic_device", selected_mic_device);
        },

        getSpeakerDeviceList: () => {
            updateSpeakerDeviceList(asyncPending);
            asyncStdoutToPython("/controller/list_speaker_device");
        },
        updateSpeakerDeviceList: (payload) => {
            updateSpeakerDeviceList(arrayToObject(payload.data));
        },
        getSelectedSpeakerDevice: () => {
            updateSelectedSpeakerDevice(asyncPending);
            asyncStdoutToPython("/config/choice_speaker_device");
        },
        updateSelectedSpeakerDevice: (payload) => {
            updateSelectedSpeakerDevice(payload.data);
        },
        setSelectedSpeakerDevice: (selected_speaker_device) => {
            updateSelectedSpeakerDevice(asyncPending);
            asyncStdoutToPython("/controller/callback_set_speaker_device", selected_speaker_device);
        },

        updateMicHostAndDevice: (payload) => {
            updateSelectedMicHost(payload.data.host);
            updateSelectedMicDevice(payload.data.device);
        },


    };
};