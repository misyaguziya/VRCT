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
import { useNotificationStatus } from "@logics_common";

export const useDevice = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { showNotification_SaveSuccess } = useNotificationStatus();

    const { currentEnableAutoMicSelect, updateEnableAutoMicSelect, pendingEnableAutoMicSelect } = useStore_EnableAutoMicSelect();
    const { currentEnableAutoSpeakerSelect, updateEnableAutoSpeakerSelect, pendingEnableAutoSpeakerSelect } = useStore_EnableAutoSpeakerSelect();

    const { currentMicDeviceList, updateMicDeviceList, pendingMicDeviceList } = useStore_MicDeviceList();
    const { currentMicHostList, updateMicHostList, pendingMicHostList } = useStore_MicHostList();
    const { currentSpeakerDeviceList, updateSpeakerDeviceList, pendingSpeakerDeviceList } = useStore_SpeakerDeviceList();

    const { currentSelectedMicHost, updateSelectedMicHost, pendingSelectedMicHost } = useStore_SelectedMicHost();
    const { currentSelectedMicDevice, updateSelectedMicDevice, pendingSelectedMicDevice } = useStore_SelectedMicDevice();

    const { currentSelectedSpeakerDevice, updateSelectedSpeakerDevice, pendingSelectedSpeakerDevice } = useStore_SelectedSpeakerDevice();

    const { currentMicThreshold, updateMicThreshold } = useStore_MicThreshold();
    const { currentEnableAutomaticMicThreshold, updateEnableAutomaticMicThreshold, pendingEnableAutomaticMicThreshold } = useStore_EnableAutomaticMicThreshold();

    const { currentSpeakerThreshold, updateSpeakerThreshold } = useStore_SpeakerThreshold();
    const { currentEnableAutomaticSpeakerThreshold, updateEnableAutomaticSpeakerThreshold, pendingEnableAutomaticSpeakerThreshold } = useStore_EnableAutomaticSpeakerThreshold();

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

    const setSuccessEnableAutoMicSelect = (enabled) => {
        updateEnableAutoMicSelect(enabled);
        showNotification_SaveSuccess();
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

    const setSuccessEnableAutoSpeakerSelect = (enabled) => {
        updateEnableAutoSpeakerSelect(enabled);
        showNotification_SaveSuccess();
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

    const setSuccessSelectedMicHost = (payload) => {
        updateSelectedMicHostAndDevice(payload); // Receive host and device from backend.
        showNotification_SaveSuccess();
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

    const setSuccessSelectedMicDevice = (selected_mic_device) => {
        updateSelectedMicDevice(selected_mic_device);
        showNotification_SaveSuccess();
    };

    // Selected (Mic Device and Host)
    const updateSelectedMicHostAndDevice = (payload) => {
        updateSelectedMicHost(payload.host);
        updateSelectedMicDevice(payload.device);
    }

    // Selected (Speaker device)
    const getSelectedSpeakerDevice = () => {
        pendingSelectedSpeakerDevice();
        asyncStdoutToPython("/get/data/selected_speaker_device");
    };

    const setSelectedSpeakerDevice = (selected_speaker_device) => {
        pendingSelectedSpeakerDevice();
        asyncStdoutToPython("/set/data/selected_speaker_device", selected_speaker_device);
    };

    const setSuccessSelectedSpeakerDevice = (selected_speaker_device) => {
        updateSelectedSpeakerDevice(selected_speaker_device);
        showNotification_SaveSuccess();
    };

    // Threshold (Mic)
    const getMicThreshold = () => {
        asyncStdoutToPython("/get/data/mic_threshold");
    };

    const setMicThreshold = (mic_threshold) => {
        asyncStdoutToPython("/set/data/mic_threshold", mic_threshold);
    };

    const setSuccessMicThreshold = (mic_threshold) => {
        updateMicThreshold(mic_threshold);
        showNotification_SaveSuccess();
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

    const setSuccessEnableAutomaticMicThreshold = (enabled) => {
        updateEnableAutomaticMicThreshold(enabled);
        showNotification_SaveSuccess();
    };

    // Threshold (Speaker)
    const getSpeakerThreshold = () => {
        asyncStdoutToPython("/get/data/speaker_threshold");
    };

    const setSpeakerThreshold = (speaker_threshold) => {
        asyncStdoutToPython("/set/data/speaker_threshold", speaker_threshold);
    };

    const setSuccessSpeakerThreshold = (speaker_threshold) => {
        updateSpeakerThreshold(speaker_threshold);
        showNotification_SaveSuccess();
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

    const setSuccessEnableAutomaticSpeakerThreshold = (enabled) => {
        updateEnableAutomaticSpeakerThreshold(enabled);
        showNotification_SaveSuccess();
    };

    return {
        currentEnableAutoMicSelect,
        getEnableAutoMicSelect,
        updateEnableAutoMicSelect,
        toggleEnableAutoMicSelect,
        setSuccessEnableAutoMicSelect,

        currentEnableAutoSpeakerSelect,
        getEnableAutoSpeakerSelect,
        updateEnableAutoSpeakerSelect,
        toggleEnableAutoSpeakerSelect,
        setSuccessEnableAutoSpeakerSelect,

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
        setSuccessSelectedMicHost,

        currentSelectedMicDevice,
        getSelectedMicDevice,
        updateSelectedMicDevice,
        setSelectedMicDevice,
        setSuccessSelectedMicDevice,
        updateSelectedMicHostAndDevice,

        currentSelectedSpeakerDevice,
        getSelectedSpeakerDevice,
        updateSelectedSpeakerDevice,
        setSelectedSpeakerDevice,
        setSuccessSelectedSpeakerDevice,

        currentMicThreshold,
        getMicThreshold,
        setMicThreshold,
        updateMicThreshold,
        setSuccessMicThreshold,

        currentEnableAutomaticMicThreshold,
        getEnableAutomaticMicThreshold,
        toggleEnableAutomaticMicThreshold,
        updateEnableAutomaticMicThreshold,
        setSuccessEnableAutomaticMicThreshold,

        currentSpeakerThreshold,
        getSpeakerThreshold,
        setSpeakerThreshold,
        updateSpeakerThreshold,
        setSuccessSpeakerThreshold,

        currentEnableAutomaticSpeakerThreshold,
        getEnableAutomaticSpeakerThreshold,
        toggleEnableAutomaticSpeakerThreshold,
        updateEnableAutomaticSpeakerThreshold,
        setSuccessEnableAutomaticSpeakerThreshold,
    };
};