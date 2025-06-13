import {
    useStore_EnableAutoMicSelect,
    useStore_EnableAutoSpeakerSelect,

    useStore_MicDeviceList,
    useStore_MicHostList,
    useStore_SpeakerDeviceList,

    useStore_SelectedMicHost,
    useStore_SelectedMicDevice,

    useStore_SelectedSpeakerDevice,

    useStore_MicThreshold,
    useStore_EnableAutomaticMicThreshold,
    useStore_SpeakerThreshold,
    useStore_EnableAutomaticSpeakerThreshold,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { arrayToObject } from "@utils";

export const useDevice = () => {
    const { asyncStdoutToPython } = useStdoutToPython();

    const { currentEnableAutoMicSelect, updateEnableAutoMicSelect, pendingEnableAutoMicSelect } = useStore_EnableAutoMicSelect();
    const { currentEnableAutoSpeakerSelect, updateEnableAutoSpeakerSelect, pendingEnableAutoSpeakerSelect } = useStore_EnableAutoSpeakerSelect();

    const { currentMicDeviceList, updateMicDeviceList, pendingMicDeviceList } = useStore_MicDeviceList();
    const { currentMicHostList, updateMicHostList, pendingMicHostList } = useStore_MicHostList();
    const { currentSpeakerDeviceList, updateSpeakerDeviceList, pendingSpeakerDeviceList } = useStore_SpeakerDeviceList();

    const { currentSelectedMicHost, updateSelectedMicHost, pendingSelectedMicHost } = useStore_SelectedMicHost();
    const { currentSelectedMicDevice, updateSelectedMicDevice, pendingSelectedMicDevice } = useStore_SelectedMicDevice();

    const { currentSelectedSpeakerDevice, updateSelectedSpeakerDevice, pendingSelectedSpeakerDevice } = useStore_SelectedSpeakerDevice();

    const { updateMicThreshold, currentMicThreshold } = useStore_MicThreshold();
    const { updateEnableAutomaticMicThreshold, currentEnableAutomaticMicThreshold, pendingEnableAutomaticMicThreshold } = useStore_EnableAutomaticMicThreshold();

    const { updateSpeakerThreshold, currentSpeakerThreshold } = useStore_SpeakerThreshold();
    const { updateEnableAutomaticSpeakerThreshold, currentEnableAutomaticSpeakerThreshold, pendingEnableAutomaticSpeakerThreshold } = useStore_EnableAutomaticSpeakerThreshold();

    // Auto Select (Mic)
    const getEnableAutoMicSelect = () => {
        pendingEnableAutoMicSelect();
        asyncStdoutToPython("/get/data/auto_mic_select");
    };

    const toggleEnableAutoMicSelect = () => {
        pendingEnableAutoMicSelect();
        if (currentEnableAutoMicSelect.data) {
            asyncStdoutToPython("/set/disable/auto_mic_select");
        } else {
            asyncStdoutToPython("/set/enable/auto_mic_select");
        }
    };
    // Auto Select (Speaker)
    const getEnableAutoSpeakerSelect = () => {
        pendingEnableAutoSpeakerSelect();
        asyncStdoutToPython("/get/data/auto_speaker_select");
    };

    const toggleEnableAutoSpeakerSelect = () => {
        pendingEnableAutoSpeakerSelect();
        if (currentEnableAutoSpeakerSelect.data) {
            asyncStdoutToPython("/set/disable/auto_speaker_select");
        } else {
            asyncStdoutToPython("/set/enable/auto_speaker_select");
        }
    };


    // List (Mic device)
    const getMicDeviceList = () => {
        pendingMicDeviceList();
        asyncStdoutToPython("/get/data/mic_device_list");
    };

    const updateMicDeviceList_FromBackend = (payload) => {
        updateMicDeviceList(arrayToObject(payload));
    };
    // List (Mic host)
    const getMicHostList = () => {
        pendingMicHostList();
        asyncStdoutToPython("/get/data/mic_host_list");
    };

    const updateMicHostList_FromBackend = (payload) => {
        updateMicHostList(arrayToObject(payload));
    };
    // List (Speaker device)
    const getSpeakerDeviceList = () => {
        pendingSpeakerDeviceList();
        asyncStdoutToPython("/get/data/speaker_device_list");
    };

    const updateSpeakerDeviceList_FromBackend = (payload) => {
        updateSpeakerDeviceList(arrayToObject(payload));
    };


    // Selected (Mic host)
    const getSelectedMicHost = () => {
        pendingSelectedMicHost();
        asyncStdoutToPython("/get/data/selected_mic_host");
    };

    const setSelectedMicHost = (selected_mic_host) => {
        pendingSelectedMicHost();
        asyncStdoutToPython("/set/data/selected_mic_host", selected_mic_host);
    };
    // Selected (Mic device)
    const getSelectedMicDevice = () => {
        pendingSelectedMicDevice();
        asyncStdoutToPython("/get/data/selected_mic_device");
    };

    const setSelectedMicDevice = (selected_mic_device) => {
        pendingSelectedMicDevice();
        asyncStdoutToPython("/set/data/selected_mic_device", selected_mic_device);
    };

    // Selected (Mic and Host)
    const updateSelectedMicHostAndDevice = (payload) => {
        updateSelectedMicHost(payload.host);
        updateSelectedMicDevice(payload.device);
    };

    // Selected (Speaker device)
    const getSelectedSpeakerDevice = () => {
        pendingSelectedSpeakerDevice();
        asyncStdoutToPython("/get/data/selected_speaker_device");
    };

    const setSelectedSpeakerDevice = (selected_speaker_device) => {
        pendingSelectedSpeakerDevice();
        asyncStdoutToPython("/set/data/selected_speaker_device", selected_speaker_device);
    };


    // Threshold (Mic)
    const getMicThreshold = () => {
        asyncStdoutToPython("/get/data/mic_threshold");
    };

    const setMicThreshold = (mic_threshold) => {
        asyncStdoutToPython("/set/data/mic_threshold", mic_threshold);
    };

    const getEnableAutomaticMicThreshold = () => {
        pendingEnableAutomaticMicThreshold();
        asyncStdoutToPython("/get/data/mic_automatic_threshold");
    };

    const toggleEnableAutomaticMicThreshold = () => {
        pendingEnableAutomaticMicThreshold();
        if (currentEnableAutomaticMicThreshold.data) {
            asyncStdoutToPython("/set/disable/mic_automatic_threshold");
        } else {
            asyncStdoutToPython("/set/enable/mic_automatic_threshold");
        }
    };
    // Threshold (Speaker)
    const getSpeakerThreshold = () => {
        asyncStdoutToPython("/get/data/speaker_threshold");
    };

    const setSpeakerThreshold = (speaker_threshold) => {
        asyncStdoutToPython("/set/data/speaker_threshold", speaker_threshold);
    };

    const getEnableAutomaticSpeakerThreshold = () => {
        pendingEnableAutomaticSpeakerThreshold();
        asyncStdoutToPython("/get/data/speaker_automatic_threshold");
    };

    const toggleEnableAutomaticSpeakerThreshold = () => {
        pendingEnableAutomaticSpeakerThreshold();
        if (currentEnableAutomaticSpeakerThreshold.data) {
            asyncStdoutToPython("/set/disable/speaker_automatic_threshold");
        } else {
            asyncStdoutToPython("/set/enable/speaker_automatic_threshold");
        }
    };



    return {
        currentEnableAutoMicSelect,
        getEnableAutoMicSelect,
        updateEnableAutoMicSelect,
        toggleEnableAutoMicSelect,

        currentEnableAutoSpeakerSelect,
        getEnableAutoSpeakerSelect,
        updateEnableAutoSpeakerSelect,
        toggleEnableAutoSpeakerSelect,


        currentMicDeviceList,
        getMicDeviceList,
        updateMicDeviceList,
        updateMicDeviceList_FromBackend,

        currentMicHostList,
        getMicHostList,
        updateMicHostList,
        updateMicHostList_FromBackend,

        currentSpeakerDeviceList,
        getSpeakerDeviceList,
        updateSpeakerDeviceList,
        updateSpeakerDeviceList_FromBackend,


        currentSelectedMicHost,
        getSelectedMicHost,
        updateSelectedMicHost,
        setSelectedMicHost,

        currentSelectedMicDevice,
        getSelectedMicDevice,
        updateSelectedMicDevice,
        setSelectedMicDevice,

        updateSelectedMicHostAndDevice,


        currentSelectedSpeakerDevice,
        getSelectedSpeakerDevice,
        updateSelectedSpeakerDevice,
        setSelectedSpeakerDevice,


        currentMicThreshold,
        getMicThreshold,
        setMicThreshold,
        updateMicThreshold,

        currentEnableAutomaticMicThreshold,
        getEnableAutomaticMicThreshold,
        toggleEnableAutomaticMicThreshold,
        updateEnableAutomaticMicThreshold,

        currentSpeakerThreshold,
        getSpeakerThreshold,
        setSpeakerThreshold,
        updateSpeakerThreshold,

        currentEnableAutomaticSpeakerThreshold,
        getEnableAutomaticSpeakerThreshold,
        toggleEnableAutomaticSpeakerThreshold,
        updateEnableAutomaticSpeakerThreshold,


    };
};