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
} from "@logics_configs";

import {
    EntryContainer,
    WordFilterContainer,
    DownloadModelsContainer,
    RadioButtonContainer,
} from "../_templates/Templates";

export const Transcription = () => {
    return (
        <>
            <Mic_Container />
            <Speaker_Container />
            <TranscriptionEngine_Container />
        </>
    );
};


const Mic_Container = () => {
    return (
        <>
            <MicRecordTimeout_Box />
            <MicPhraseTimeout_Box />
            <MicMaxWords_Box />
            <MicWordFilter_Box />
        </>
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
            label={t("config_page.mic_record_timeout.label")}
            desc={t("config_page.mic_record_timeout.desc")}
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
            label={t("config_page.mic_phrase_timeout.label")}
            desc={t("config_page.mic_phrase_timeout.desc")}
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
            label={t("config_page.mic_max_phrase.label")}
            desc={t("config_page.mic_max_phrase.desc")}
            ui_variable={ui_variable}
            onChange={onChangeFunction}
        />
    );
};

const MicWordFilter_Box = () => {
    const { t } = useTranslation();

    return (
        <WordFilterContainer
            label={t("config_page.mic_word_filter.label")}
            desc={t("config_page.mic_word_filter.desc")}
        />
    );
};




const Speaker_Container = () => {
    return (
        <>
            <SpeakerRecordTimeout_Box />
            <SpeakerPhraseTimeout_Box />
            <SpeakerMaxWords_Box />
        </>
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
            label={t("config_page.speaker_record_timeout.label")}
            desc={t("config_page.speaker_record_timeout.desc")}
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
            label={t("config_page.speaker_phrase_timeout.label")}
            desc={t("config_page.speaker_phrase_timeout.desc")}
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
            label={t("config_page.speaker_max_phrase.label")}
            desc={t("config_page.speaker_max_phrase.desc")}
            ui_variable={ui_variable}
            onChange={onChangeFunction}
        />
    );
};



const TranscriptionEngine_Container = () => {
    return (
        <>
            <TranscriptionEngine_Box />
            <WhisperWeightType_Box />
        </>
    );
};

const TranscriptionEngine_Box = () => {
    const { t } = useTranslation();
    const { currentSelectedTranscriptionEngine, setSelectedTranscriptionEngine } = useSelectedTranscriptionEngine();

    return (
        <RadioButtonContainer
            label={t("config_page.select_transcription_engine.label")}
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
        { id: "tiny", label: t("config_page.whisper_weight_type.model_template", {model_name: "tiny", capacity: "74.5MB"}) },
        { id: "base", label: t("config_page.whisper_weight_type.recommended_model_template", {model_name: "base", capacity: "141MB"}) },
        { id: "small", label: t("config_page.whisper_weight_type.model_template", {model_name: "small", capacity: "463MB"}) },
        { id: "medium", label: t("config_page.whisper_weight_type.model_template", {model_name: "medium", capacity: "1.42GB"}) },
        { id: "large-v1", label: t("config_page.whisper_weight_type.model_template", {model_name: "large-v1", capacity: "2.87GB"}) },
        { id: "large-v2", label: t("config_page.whisper_weight_type.model_template", {model_name: "large-v2", capacity: "2.87GB"}) },
        { id: "large-v3", label: t("config_page.whisper_weight_type.model_template", {model_name: "large-v3", capacity: "2.87GB"}) },
    ];

    const whisper_weight_types = updateLabelsById(currentWhisperWeightTypeStatus.data, new_labels);

    return (
        <>
            <DownloadModelsContainer
                label={t("config_page.whisper_weight_type.label")}
                desc={t(
                    "config_page.whisper_weight_type.desc",
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