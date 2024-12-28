import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import styles from "./Transcription.module.scss";
import { updateLabelsById } from "@utils";

import {
    useMicRecordTimeout,
    useMicPhraseTimeout,
    useMicMaxWords,

    useSpeakerRecordTimeout,
    useSpeakerPhraseTimeout,
    useSpeakerMaxWords,

    useSelectedTranscriptionEngine,
    useWhisperWeightTypeStatus,
    useSelectedWhisperWeightType,

    useSelectedWhisperComputeDevice,
    useSelectableWhisperComputeDeviceList,
} from "@logics_configs";

import {
    EntryContainer,
    WordFilterContainer,
    DownloadModelsContainer,
    RadioButtonContainer,
    DropdownMenuContainer,
} from "../_templates/Templates";

import {
    SectionLabelComponent,
} from "../_components/";

export const Transcription = () => {
    return (
        <div className={styles.container}>
            <Mic_Container />
            <Speaker_Container />
            <TranscriptionEngine_Container />
        </div>
    );
};


const Mic_Container = () => {
    const { t } = useTranslation();
    return (
        <div>
            <SectionLabelComponent label={t("config_page.transcription.section_label_mic")} />
            <MicRecordTimeout_Box />
            <MicPhraseTimeout_Box />
            <MicMaxWords_Box />
            <MicWordFilter_Box />
        </div>
    );
};

const MicRecordTimeout_Box = () => {
    const { t } = useTranslation();
    const [ui_variable, setUiVariable] = useState("");
    const { currentMicRecordTimeout, setMicRecordTimeout } = useMicRecordTimeout();
    const onChangeFunction = (e) => {
        const value = e.currentTarget.value;
        if (value === "") {
            setUiVariable("");
        } else {
            setUiVariable(value);
            setMicRecordTimeout(value);
        }
    };

    useEffect(()=> {
        setUiVariable(currentMicRecordTimeout.data);
    }, [currentMicRecordTimeout]);

    return (
        <EntryContainer
            label={t("config_page.transcription.mic_record_timeout.label")}
            desc={t("config_page.transcription.mic_record_timeout.desc")}
            ui_variable={ui_variable}
            onChange={onChangeFunction}
        />
    );
};
const MicPhraseTimeout_Box = () => {
    const { t } = useTranslation();
    const [ui_variable, setUiVariable] = useState("");
    const { currentMicPhraseTimeout, setMicPhraseTimeout } = useMicPhraseTimeout();
    const onChangeFunction = (e) => {
        const value = e.currentTarget.value;
        if (value === "") {
            setUiVariable("");
        } else {
            setUiVariable(value);
            setMicPhraseTimeout(value);
        }
    };

    useEffect(()=> {
        setUiVariable(currentMicPhraseTimeout.data);
    }, [currentMicPhraseTimeout]);

    return (
        <EntryContainer
            label={t("config_page.transcription.mic_phrase_timeout.label")}
            desc={t("config_page.transcription.mic_phrase_timeout.desc")}
            ui_variable={ui_variable}
            onChange={onChangeFunction}
        />
    );
};
const MicMaxWords_Box = () => {
    const { t } = useTranslation();
    const [ui_variable, setUiVariable] = useState("");
    const { currentMicMaxWords, setMicMaxWords } = useMicMaxWords();
    const onChangeFunction = (e) => {
        const value = e.currentTarget.value;
        if (value === "") {
            setUiVariable("");
        } else {
            setUiVariable(value);
            setMicMaxWords(value);
        }
    };

    useEffect(()=> {
        setUiVariable(currentMicMaxWords.data);
    }, [currentMicMaxWords]);

    return (
        <EntryContainer
            label={t("config_page.transcription.mic_max_phrase.label")}
            desc={t("config_page.transcription.mic_max_phrase.desc")}
            ui_variable={ui_variable}
            onChange={onChangeFunction}
        />
    );
};

const MicWordFilter_Box = () => {
    const { t } = useTranslation();

    return (
        <WordFilterContainer
            label={t("config_page.transcription.mic_word_filter.label")}
            desc={t("config_page.transcription.mic_word_filter.desc")}
        />
    );
};




const Speaker_Container = () => {
    const { t } = useTranslation();
    return (
        <div>
            <SectionLabelComponent label={t("config_page.transcription.section_label_speaker")} />
            <SpeakerRecordTimeout_Box />
            <SpeakerPhraseTimeout_Box />
            <SpeakerMaxWords_Box />
        </div>
    );
};

const SpeakerRecordTimeout_Box = () => {
    const { t } = useTranslation();
    const [ui_variable, setUiVariable] = useState("");
    const { currentSpeakerRecordTimeout, setSpeakerRecordTimeout } = useSpeakerRecordTimeout();
    const onChangeFunction = (e) => {
        const value = e.currentTarget.value;
        if (value === "") {
            setUiVariable("");
        } else {
            setUiVariable(value);
            setSpeakerRecordTimeout(value);
        }
    };

    useEffect(()=> {
        setUiVariable(currentSpeakerRecordTimeout.data);
    }, [currentSpeakerRecordTimeout]);

    return (
        <EntryContainer
            label={t("config_page.transcription.speaker_record_timeout.label")}
            desc={t("config_page.transcription.speaker_record_timeout.desc")}
            ui_variable={ui_variable}
            onChange={onChangeFunction}
        />
    );
};
const SpeakerPhraseTimeout_Box = () => {
    const { t } = useTranslation();
    const [ui_variable, setUiVariable] = useState("");
    const { currentSpeakerPhraseTimeout, setSpeakerPhraseTimeout } = useSpeakerPhraseTimeout();
    const onChangeFunction = (e) => {
        const value = e.currentTarget.value;
        if (value === "") {
            setUiVariable("");
        } else {
            setUiVariable(value);
            setSpeakerPhraseTimeout(value);
        }
    };

    useEffect(()=> {
        setUiVariable(currentSpeakerPhraseTimeout.data);
    }, [currentSpeakerPhraseTimeout]);

    return (
        <EntryContainer
            label={t("config_page.transcription.speaker_phrase_timeout.label")}
            desc={t("config_page.transcription.speaker_phrase_timeout.desc")}
            ui_variable={ui_variable}
            onChange={onChangeFunction}
        />
    );
};
const SpeakerMaxWords_Box = () => {
    const { t } = useTranslation();
    const [ui_variable, setUiVariable] = useState("");
    const { currentSpeakerMaxWords, setSpeakerMaxWords } = useSpeakerMaxWords();
    const onChangeFunction = (e) => {
        const value = e.currentTarget.value;
        if (value === "") {
            setUiVariable("");
        } else {
            setUiVariable(value);
            setSpeakerMaxWords(value);
        }
    };

    useEffect(()=> {
        setUiVariable(currentSpeakerMaxWords.data);
    }, [currentSpeakerMaxWords]);

    return (
        <EntryContainer
            label={t("config_page.transcription.speaker_max_phrase.label")}
            desc={t("config_page.transcription.speaker_max_phrase.desc")}
            ui_variable={ui_variable}
            onChange={onChangeFunction}
        />
    );
};



const TranscriptionEngine_Container = () => {
    const { t } = useTranslation();
    return (
        <div>
            <SectionLabelComponent label={t("config_page.transcription.section_label_transcription_engines")} />
            <TranscriptionEngine_Box />
            <WhisperWeightType_Box />
            <WhisperComputeDevice_Box />
        </div>
    );
};

const TranscriptionEngine_Box = () => {
    const { t } = useTranslation();
    const { currentSelectedTranscriptionEngine, setSelectedTranscriptionEngine } = useSelectedTranscriptionEngine();

    return (
        <RadioButtonContainer
            label={t("config_page.transcription.select_transcription_engine.label")}
            selectFunction={setSelectedTranscriptionEngine}
            name="select_transcription_engine"
            options={[
                { id: "Google", label: "Google" },
                { id: "Whisper", label: "Whisper" },
            ]}
            checked_variable={currentSelectedTranscriptionEngine}
        />
    );
};

const WhisperWeightType_Box = () => {
    const { t } = useTranslation();
    const {
        currentWhisperWeightTypeStatus,
        pendingWhisperWeightType,
        downloadWhisperWeight,
    } = useWhisperWeightTypeStatus();
    const { currentSelectedWhisperWeightType, setSelectedWhisperWeightType } = useSelectedWhisperWeightType();

    const selectFunction = (id) => {
        setSelectedWhisperWeightType(id);
    };

    const downloadStartFunction = (id) => {
        pendingWhisperWeightType(id);
        downloadWhisperWeight(id);
    };

    const new_labels = [
        { id: "tiny", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "tiny", capacity: "74.5MB"}) },
        { id: "base", label: t("config_page.transcription.whisper_weight_type.recommended_model_template", {model_name: "base", capacity: "141MB"}) },
        { id: "small", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "small", capacity: "463MB"}) },
        { id: "medium", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "medium", capacity: "1.42GB"}) },
        { id: "large-v1", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "large-v1", capacity: "2.87GB"}) },
        { id: "large-v2", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "large-v2", capacity: "2.87GB"}) },
        { id: "large-v3", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "large-v3", capacity: "2.87GB"}) },
    ];

    const whisper_weight_types = updateLabelsById(currentWhisperWeightTypeStatus.data, new_labels);

    return (
        <>
            <DownloadModelsContainer
                label={t("config_page.transcription.whisper_weight_type.label")}
                desc={t(
                    "config_page.transcription.whisper_weight_type.desc",
                    {translator: t("main_page.translator")}
                )}
                name="whisper_weight_type"
                options={whisper_weight_types}
                checked_variable={currentSelectedWhisperWeightType}
                selectFunction={selectFunction}
                downloadStartFunction={downloadStartFunction}
            />
        </>
    );
};

const WhisperComputeDevice_Box = () => {
    const { t } = useTranslation();
    const { currentSelectedWhisperComputeDevice, setSelectedWhisperComputeDevice } = useSelectedWhisperComputeDevice();
    const { currentSelectableWhisperComputeDeviceList } = useSelectableWhisperComputeDeviceList();

    const selectFunction = (selected_data) => {
        const target_obj = currentSelectableWhisperComputeDeviceList.data[selected_data.selected_id];
        setSelectedWhisperComputeDevice(target_obj);
    };

    const list_for_ui = transformDeviceArray(currentSelectableWhisperComputeDeviceList.data);

    const target_index = findKeyByDeviceValue(currentSelectableWhisperComputeDeviceList.data, currentSelectedWhisperComputeDevice.data);


    return (
        <DropdownMenuContainer
            dropdown_id="whisper_compute_device"
            label={t("config_page.transcription.whisper_compute_device.label")}
            // desc={t("config_page.transcription.whisper_compute_device.label")}
            selected_id={target_index}
            list={list_for_ui}
            selectFunction={selectFunction}
            state={currentSelectedWhisperComputeDevice.state}
        />
    );
};

// Duplicate
const transformDeviceArray = (devices) => {
    const name_counts = Object.values(devices).reduce((counts, device) => {
        const name = device.device_name;
        counts[name] = (counts[name] || 0) + 1;
        return counts;
    }, {});

    const name_indices = {};
    const result = {};

    Object.entries(devices).forEach(([key, device]) => {
        const name = device.device_name;

        if (name_counts[name] > 1) {
            name_indices[name] = (name_indices[name] || 0);
            const value = `${name}:${name_indices[name]}`;
            name_indices[name]++;
            result[key] = value;
        } else {
            result[key] = name;
        }
    });

    return result;
};

const findKeyByDeviceValue = (devices, target_value) => {
    for (const [key, value] of Object.entries(devices)) {
        if (
            value.device === target_value.device &&
            value.device_index === target_value.device_index &&
            value.device_name === target_value.device_name
        ) {
            return parseInt(key);
        }
    }
    return null;
};