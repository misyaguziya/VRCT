import {
    useStore_MicRecordTimeout,
    useStore_MicPhraseTimeout,
    useStore_MicMaxWords,
    useStore_MicWordFilterList,

    useStore_SpeakerMaxWords,
    useStore_SpeakerPhraseTimeout,
    useStore_SpeakerRecordTimeout,

    useStore_SelectableTranscriptionComputeDeviceList,
    useStore_SelectedTranscriptionEngine,
    useStore_SelectedTranscriptionComputeDevice,

    useStore_WhisperWeightTypeStatus,
    useStore_SelectedWhisperWeightType,
    useStore_SelectedTranscriptionComputeType,

    useStore_MicAvgLogprob,
    useStore_MicNoSpeechProb,
    useStore_SpeakerAvgLogprob,
    useStore_SpeakerNoSpeechProb,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { transformToIndexedArray, arrayToObject } from "@utils";
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


    const { currentSelectedTranscriptionComputeType, updateSelectedTranscriptionComputeType, pendingSelectedTranscriptionComputeType } = useStore_SelectedTranscriptionComputeType();

    const { currentSelectableTranscriptionComputeDeviceList, updateSelectableTranscriptionComputeDeviceList, pendingSelectableTranscriptionComputeDeviceList } = useStore_SelectableTranscriptionComputeDeviceList();
    const { currentSelectedTranscriptionComputeDevice, updateSelectedTranscriptionComputeDevice, pendingSelectedTranscriptionComputeDevice } = useStore_SelectedTranscriptionComputeDevice();

    // Advanced Settings
    const { currentMicAvgLogprob, updateMicAvgLogprob, pendingMicAvgLogprob } = useStore_MicAvgLogprob();
    const { currentMicNoSpeechProb, updateMicNoSpeechProb, pendingMicNoSpeechProb } = useStore_MicNoSpeechProb();
    const { currentSpeakerAvgLogprob, updateSpeakerAvgLogprob, pendingSpeakerAvgLogprob } = useStore_SpeakerAvgLogprob();
    const { currentSpeakerNoSpeechProb, updateSpeakerNoSpeechProb, pendingSpeakerNoSpeechProb } = useStore_SpeakerNoSpeechProb();


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

    const getSuccessMicWordFilterList = (payload) => {
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



    const getSelectedTranscriptionComputeType = () => {
        pendingSelectedTranscriptionComputeType();
        asyncStdoutToPython("/get/data/selected_transcription_compute_type");
    };

    const setSelectedTranscriptionComputeType = (selected_transcription_compute_type) => {
        pendingSelectedTranscriptionComputeType();
        asyncStdoutToPython("/set/data/selected_transcription_compute_type", selected_transcription_compute_type);
    };

    const setSuccessSelectedTranscriptionComputeType = (selected_transcription_compute_type) => {
        updateSelectedTranscriptionComputeType(selected_transcription_compute_type);
        showNotification_SaveSuccess();
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
    const getSelectableTranscriptionComputeDeviceList = () => {
        pendingSelectableTranscriptionComputeDeviceList();
        asyncStdoutToPython("/get/data/transcription_compute_device_list");
    };

    const updateSelectableTranscriptionComputeDeviceList_FromBackend = (payload) => {
        updateSelectableTranscriptionComputeDeviceList(transformToIndexedArray(payload));
    };

    // Transcription Engines (Selected Compute Device)
    const getSelectedTranscriptionComputeDevice = () => {
        pendingSelectedTranscriptionComputeDevice();
        asyncStdoutToPython("/get/data/selected_transcription_compute_device");
    };

    const setSelectedTranscriptionComputeDevice = (selected_transcription_compute_device) => {
        pendingSelectedTranscriptionComputeDevice();
        asyncStdoutToPython("/set/data/selected_transcription_compute_device", selected_transcription_compute_device);
    };

    const setSuccessSelectedTranscriptionComputeDevice = (dev) => {
        updateSelectedTranscriptionComputeDevice(dev);
        showNotification_SaveSuccess();
    };

    // Advanced (Mic Avg Logprob)
    const getMicAvgLogprob = () => {
        pendingMicAvgLogprob();
        asyncStdoutToPython("/get/data/mic_avg_logprob");
    };

    const setMicAvgLogprob = (selected_mic_avg_logprob) => {
        pendingMicAvgLogprob();
        asyncStdoutToPython("/set/data/mic_avg_logprob", selected_mic_avg_logprob);
    };

    const setSuccessMicAvgLogprob = (selected_mic_avg_logprob) => {
        updateMicAvgLogprob(selected_mic_avg_logprob);
        showNotification_SaveSuccess();
    };
    // Advanced (Mic No Speech Prob)
    const getMicNoSpeechProb = () => {
        pendingMicNoSpeechProb();
        asyncStdoutToPython("/get/data/mic_no_speech_prob");
    };

    const setMicNoSpeechProb = (selected_mic_no_speech_prob) => {
        pendingMicNoSpeechProb();
        asyncStdoutToPython("/set/data/mic_no_speech_prob", selected_mic_no_speech_prob);
    };

    const setSuccessMicNoSpeechProb = (selected_mic_no_speech_prob) => {
        updateMicNoSpeechProb(selected_mic_no_speech_prob);
        showNotification_SaveSuccess();
    };
    // Advanced (Speaker Avg Logprob)
    const getSpeakerAvgLogprob = () => {
        pendingSpeakerAvgLogprob();
        asyncStdoutToPython("/get/data/speaker_avg_logprob");
    };

    const setSpeakerAvgLogprob = (selected_speaker_avg_logprob) => {
        pendingSpeakerAvgLogprob();
        asyncStdoutToPython("/set/data/speaker_avg_logprob", selected_speaker_avg_logprob);
    };

    const setSuccessSpeakerAvgLogprob = (selected_speaker_avg_logprob) => {
        updateSpeakerAvgLogprob(selected_speaker_avg_logprob);
        showNotification_SaveSuccess();
    };
    // Advanced (Speaker No Speech Prob)
    const getSpeakerNoSpeechProb = () => {
        pendingSpeakerNoSpeechProb();
        asyncStdoutToPython("/get/data/speaker_no_speech_prob");
    };

    const setSpeakerNoSpeechProb = (selected_speaker_no_speech_prob) => {
        pendingSpeakerNoSpeechProb();
        asyncStdoutToPython("/set/data/speaker_no_speech_prob", selected_speaker_no_speech_prob);
    };

    const setSuccessSpeakerNoSpeechProb = (selected_speaker_no_speech_prob) => {
        updateSpeakerNoSpeechProb(selected_speaker_no_speech_prob);
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
        getSuccessMicWordFilterList,
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


        currentSelectedTranscriptionComputeType,
        getSelectedTranscriptionComputeType,
        updateSelectedTranscriptionComputeType,
        setSelectedTranscriptionComputeType,
        setSuccessSelectedTranscriptionComputeType,


        currentSelectableTranscriptionComputeDeviceList,
        getSelectableTranscriptionComputeDeviceList,
        updateSelectableTranscriptionComputeDeviceList,
        updateSelectableTranscriptionComputeDeviceList_FromBackend,

        currentSelectedTranscriptionComputeDevice,
        getSelectedTranscriptionComputeDevice,
        updateSelectedTranscriptionComputeDevice,
        setSelectedTranscriptionComputeDevice,
        setSuccessSelectedTranscriptionComputeDevice,

        // Advanced
        // Mic Avg Logprob
        currentMicAvgLogprob,
        getMicAvgLogprob,
        updateMicAvgLogprob,
        setMicAvgLogprob,
        setSuccessMicAvgLogprob,
        // Mic No Speech Prob
        currentMicNoSpeechProb,
        getMicNoSpeechProb,
        updateMicNoSpeechProb,
        setMicNoSpeechProb,
        setSuccessMicNoSpeechProb,
        // Speaker Avg Logprob
        currentSpeakerAvgLogprob,
        getSpeakerAvgLogprob,
        updateSpeakerAvgLogprob,
        setSpeakerAvgLogprob,
        setSuccessSpeakerAvgLogprob,
        // Speaker No Speech Prob
        currentSpeakerNoSpeechProb,
        getSpeakerNoSpeechProb,
        updateSpeakerNoSpeechProb,
        setSpeakerNoSpeechProb,
        setSuccessSpeakerNoSpeechProb,
    };
};