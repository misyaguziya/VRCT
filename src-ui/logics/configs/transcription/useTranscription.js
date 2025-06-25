import {
    useStore_MicRecordTimeout,
    useStore_MicPhraseTimeout,
    useStore_MicMaxWords,
    useStore_MicWordFilterList,

    useStore_SpeakerMaxWords,
    useStore_SpeakerPhraseTimeout,
    useStore_SpeakerRecordTimeout,

    useStore_SelectableWhisperComputeDeviceList,
    useStore_SelectedTranscriptionEngine,
    useStore_SelectedWhisperComputeDevice,
    useStore_SelectedWhisperWeightType,

    useStore_WhisperWeightTypeStatus,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { transformToIndexedArray } from "@utils";
import { useNotificationStatus } from "@logics_common";

export const useTranscription = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { showNotification_SaveSuccess } = useNotificationStatus();

    // Mic
    const { currentMicRecordTimeout, updateMicRecordTimeout, pendingMicRecordTimeout } = useStore_MicRecordTimeout();
    const { currentMicPhraseTimeout, updateMicPhraseTimeout, pendingMicPhraseTimeout } = useStore_MicPhraseTimeout();
    const { currentMicMaxWords, updateMicMaxWords, pendingMicMaxWords } = useStore_MicMaxWords();
    const { currentMicWordFilterList, updateMicWordFilterList, pendingMicWordFilterList } = useStore_MicWordFilterList();

    // Speaker
    const { currentSpeakerRecordTimeout, updateSpeakerRecordTimeout, pendingSpeakerRecordTimeout } = useStore_SpeakerRecordTimeout();
    const { currentSpeakerPhraseTimeout, updateSpeakerPhraseTimeout, pendingSpeakerPhraseTimeout } = useStore_SpeakerPhraseTimeout();
    const { currentSpeakerMaxWords, updateSpeakerMaxWords, pendingSpeakerMaxWords } = useStore_SpeakerMaxWords();

    // Transcription Engines
    const { currentSelectedTranscriptionEngine, updateSelectedTranscriptionEngine, pendingSelectedTranscriptionEngine } = useStore_SelectedTranscriptionEngine();
    const { currentWhisperWeightTypeStatus, updateWhisperWeightTypeStatus, pendingWhisperWeightTypeStatus } = useStore_WhisperWeightTypeStatus();
    const { currentSelectedWhisperWeightType, updateSelectedWhisperWeightType, pendingSelectedWhisperWeightType } = useStore_SelectedWhisperWeightType();
    const { currentSelectableWhisperComputeDeviceList, updateSelectableWhisperComputeDeviceList, pendingSelectableWhisperComputeDeviceList } = useStore_SelectableWhisperComputeDeviceList();
    const { currentSelectedWhisperComputeDevice, updateSelectedWhisperComputeDevice, pendingSelectedWhisperComputeDevice } = useStore_SelectedWhisperComputeDevice();

    // Mic
    const getMicRecordTimeout = () => {
        pendingMicRecordTimeout();
        asyncStdoutToPython("/get/data/mic_record_timeout");
    };

    const setMicRecordTimeout = (selected_mic_record_timeout) => {
        pendingMicRecordTimeout();
        asyncStdoutToPython("/set/data/mic_record_timeout", selected_mic_record_timeout);
    };

    const setSuccessMicRecordTimeout = (value) => {
        updateMicRecordTimeout(value);
        showNotification_SaveSuccess();
    };

    const getMicPhraseTimeout = () => {
        pendingMicPhraseTimeout();
        asyncStdoutToPython("/get/data/mic_phrase_timeout");
    };

    const setMicPhraseTimeout = (selected_mic_phrase_timeout) => {
        pendingMicPhraseTimeout();
        asyncStdoutToPython("/set/data/mic_phrase_timeout", selected_mic_phrase_timeout);
    };

    const setSuccessMicPhraseTimeout = (value) => {
        updateMicPhraseTimeout(value);
        showNotification_SaveSuccess();
    };

    const getMicMaxWords = () => {
        pendingMicMaxWords();
        asyncStdoutToPython("/get/data/mic_max_phrases");
    };

    const setMicMaxWords = (selected_mic_max_phrases) => {
        pendingMicMaxWords();
        asyncStdoutToPython("/set/data/mic_max_phrases", selected_mic_max_phrases);
    };

    const setSuccessMicMaxWords = (value) => {
        updateMicMaxWords(value);
        showNotification_SaveSuccess();
    };

    const getMicWordFilterList = () => {
        pendingMicWordFilterList();
        asyncStdoutToPython("/get/data/mic_word_filter");
    };

    const setMicWordFilterList = (selected_mic_word_filter) => {
        pendingMicWordFilterList();
        asyncStdoutToPython("/set/data/mic_word_filter", selected_mic_word_filter);
    };

    const setSuccessMicWordFilterList = (payload) => {
        updateMicWordFilterList((prev_list) => {
            const updated_list = [...prev_list.data];
            for (const value of payload) {
                const existing_item = updated_list.find(item => item.value === value);
                if (existing_item) {
                    existing_item.is_redoable = false;
                } else {
                    updated_list.push({ value, is_redoable: false });
                }
            }
            return updated_list;
        });
        showNotification_SaveSuccess();
    };

    // Speaker
    const getSpeakerRecordTimeout = () => {
        pendingSpeakerRecordTimeout();
        asyncStdoutToPython("/get/data/speaker_record_timeout");
    };

    const setSpeakerRecordTimeout = (selected_speaker_record_timeout) => {
        pendingSpeakerRecordTimeout();
        asyncStdoutToPython("/set/data/speaker_record_timeout", selected_speaker_record_timeout);
    };

    const setSuccessSpeakerRecordTimeout = (value) => {
        updateSpeakerRecordTimeout(value);
        showNotification_SaveSuccess();
    };

    const getSpeakerPhraseTimeout = () => {
        pendingSpeakerPhraseTimeout();
        asyncStdoutToPython("/get/data/speaker_phrase_timeout");
    };

    const setSpeakerPhraseTimeout = (selected_speaker_phrase_timeout) => {
        pendingSpeakerPhraseTimeout();
        asyncStdoutToPython("/set/data/speaker_phrase_timeout", selected_speaker_phrase_timeout);
    };

    const setSuccessSpeakerPhraseTimeout = (value) => {
        updateSpeakerPhraseTimeout(value);
        showNotification_SaveSuccess();
    };

    const getSpeakerMaxWords = () => {
        pendingSpeakerMaxWords();
        asyncStdoutToPython("/get/data/speaker_max_phrases");
    };

    const setSpeakerMaxWords = (selected_speaker_max_phrases) => {
        pendingSpeakerMaxWords();
        asyncStdoutToPython("/set/data/speaker_max_phrases", selected_speaker_max_phrases);
    };

    const setSuccessSpeakerMaxWords = (value) => {
        updateSpeakerMaxWords(value);
        showNotification_SaveSuccess();
    };

    // Transcription Engines
    // Transcription Engines (Google / Whisper)
    const getSelectedTranscriptionEngine = () => {
        pendingSelectedTranscriptionEngine();
        asyncStdoutToPython("/get/data/selected_transcription_engine");
    };

    const setSelectedTranscriptionEngine = (selected_transcription_engine) => {
        pendingSelectedTranscriptionEngine();
        asyncStdoutToPython("/set/data/selected_transcription_engine", selected_transcription_engine);
    };

    const setSuccessSelectedTranscriptionEngine = (engine) => {
        updateSelectedTranscriptionEngine(engine);
        showNotification_SaveSuccess();
    };

    // Transcription Engines (Weight Type List)
    const updateDownloadedWhisperWeightTypeStatus = (downloaded_weight_type_status) => {
        updateWhisperWeightTypeStatus((old_status) =>
            old_status.data.map((item) => ({
                ...item,
                is_downloaded: downloaded_weight_type_status[item.id] ?? item.is_downloaded,
            }))
        );
    };
    const updateDownloadProgressWhisperWeightTypeStatus = (payload) => {
        if (payload === true) return console.error("fix me.");

        updateWhisperWeightTypeStatus((old_status) =>
            old_status.data.map((item) =>
                payload.weight_type === item.id
                    ? { ...item, progress: payload.progress * 100 }
                    : item
            )
        );
    };
    const pendingWhisperWeightType = (id) => {
        updateWhisperWeightTypeStatus((old_status) =>
            old_status.data.map((item) =>
                id === item.id
                    ? { ...item, is_pending: true }
                    : item
            )
        );
    };
    const downloadedWhisperWeightType = (id) => {
        updateWhisperWeightTypeStatus((old_status) =>
            old_status.data.map((item) =>
                id === item.id
                    ? { ...item, is_downloaded: true, is_pending: false, progress: null }
                    : item
            )
        );
    };

    const downloadWhisperWeight = (weight_type) => {
        asyncStdoutToPython("/run/download_whisper_weight", weight_type);
    };

    // Transcription Engines (Selected Weight Type)
    const getSelectedWhisperWeightType = () => {
        pendingSelectedWhisperWeightType();
        asyncStdoutToPython("/get/data/whisper_weight_type");
    };

    const setSelectedWhisperWeightType = (selected_whisper_weight_type) => {
        pendingSelectedWhisperWeightType();
        asyncStdoutToPython("/set/data/whisper_weight_type", selected_whisper_weight_type);
    };

    const setSuccessSelectedWhisperWeightType = (wt) => {
        updateSelectedWhisperWeightType(wt);
        showNotification_SaveSuccess();
    };

    // Transcription Engines (Compute Device List)
    const getSelectableWhisperComputeDeviceList = () => {
        pendingSelectableWhisperComputeDeviceList();
        asyncStdoutToPython("/get/data/transcription_compute_device_list");
    };

    const updateSelectableWhisperComputeDeviceList_FromBackend = (payload) => {
        updateSelectableWhisperComputeDeviceList(transformToIndexedArray(payload));
    };

    // Transcription Engines (Selected Compute Device)
    const getSelectedWhisperComputeDevice = () => {
        pendingSelectedWhisperComputeDevice();
        asyncStdoutToPython("/get/data/selected_transcription_compute_device");
    };

    const setSelectedWhisperComputeDevice = (selected_transcription_compute_device) => {
        pendingSelectedWhisperComputeDevice();
        asyncStdoutToPython("/set/data/selected_transcription_compute_device", selected_transcription_compute_device);
    };

    const setSuccessSelectedWhisperComputeDevice = (dev) => {
        updateSelectedWhisperComputeDevice(dev);
        showNotification_SaveSuccess();
    };

    return {
        // Mic
        currentMicRecordTimeout,
        getMicRecordTimeout,
        updateMicRecordTimeout,
        setMicRecordTimeout,
        setSuccessMicRecordTimeout,

        currentMicPhraseTimeout,
        getMicPhraseTimeout,
        updateMicPhraseTimeout,
        setMicPhraseTimeout,
        setSuccessMicPhraseTimeout,

        currentMicMaxWords,
        getMicMaxWords,
        updateMicMaxWords,
        setMicMaxWords,
        setSuccessMicMaxWords,

        currentMicWordFilterList,
        getMicWordFilterList,
        updateMicWordFilterList,
        setMicWordFilterList,
        setSuccessMicWordFilterList,

        // Speaker
        currentSpeakerRecordTimeout,
        getSpeakerRecordTimeout,
        updateSpeakerRecordTimeout,
        setSpeakerRecordTimeout,
        setSuccessSpeakerRecordTimeout,

        currentSpeakerPhraseTimeout,
        getSpeakerPhraseTimeout,
        updateSpeakerPhraseTimeout,
        setSpeakerPhraseTimeout,
        setSuccessSpeakerPhraseTimeout,

        currentSpeakerMaxWords,
        getSpeakerMaxWords,
        updateSpeakerMaxWords,
        setSpeakerMaxWords,
        setSuccessSpeakerMaxWords,

        // Transcription Engines
        currentSelectedTranscriptionEngine,
        getSelectedTranscriptionEngine,
        updateSelectedTranscriptionEngine,
        setSelectedTranscriptionEngine,
        setSuccessSelectedTranscriptionEngine,

        currentWhisperWeightTypeStatus,
        updateWhisperWeightTypeStatus,
        updateDownloadedWhisperWeightTypeStatus,
        updateDownloadProgressWhisperWeightTypeStatus,
        pendingWhisperWeightType,
        downloadedWhisperWeightType,
        downloadWhisperWeight,

        currentSelectedWhisperWeightType,
        getSelectedWhisperWeightType,
        updateSelectedWhisperWeightType,
        setSelectedWhisperWeightType,
        setSuccessSelectedWhisperWeightType,

        currentSelectableWhisperComputeDeviceList,
        getSelectableWhisperComputeDeviceList,
        updateSelectableWhisperComputeDeviceList,
        updateSelectableWhisperComputeDeviceList_FromBackend,

        currentSelectedWhisperComputeDevice,
        getSelectedWhisperComputeDevice,
        updateSelectedWhisperComputeDevice,
        setSelectedWhisperComputeDevice,
        setSuccessSelectedWhisperComputeDevice,
    };
};