import { useEffect, useState } from "react";
import { useI18n } from "@useI18n";
import styles from "./Transcription.module.scss";
import { updateLabelsById, genNumObjArray, arrayToObject } from "@utils";
import { useStore_IsBreakPoint } from "@store";

import {
    useTranscription,
} from "@logics_configs";

import {
    WordFilterContainer,
    DownloadModelsContainer,
    RadioButtonContainer,
    DropdownMenuContainer,
    SliderContainer,

    useOnMouseLeaveDropdownMenu,
} from "../_templates/Templates";

import {
    DropdownMenu,
    LabelComponent,
    SectionLabelComponent,
} from "../_components/";

export const Transcription = () => {
    return (
        <div className={styles.container}>
            <Mic_Container />
            <Speaker_Container />
            <TranscriptionEngine_Container />
            <Advanced_Container />
        </div>
    );
};


const Mic_Container = () => {
    const { t } = useI18n();
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
    const { t } = useI18n();
    const { currentMicRecordTimeout, setMicRecordTimeout } = useTranscription();

    const selectFunction = (selected_data) => {
        setMicRecordTimeout(selected_data.selected_id);
    };

    return (
        <DropdownMenuContainer
            dropdown_id="mic_record_timeout"
            label={t("config_page.transcription.mic_record_timeout.label")}
            desc={t("config_page.transcription.mic_record_timeout.desc")}
            selected_id={currentMicRecordTimeout.data}
            list={genNumObjArray(31)}
            selectFunction={selectFunction}
            state={currentMicRecordTimeout.state}
        />
    );
};
const MicPhraseTimeout_Box = () => {
    const { t } = useI18n();
    const { currentMicPhraseTimeout, setMicPhraseTimeout } = useTranscription();

    const selectFunction = (selected_data) => {
        setMicPhraseTimeout(selected_data.selected_id);
    };

    return (
        <DropdownMenuContainer
            dropdown_id="mic_phrase_timeout"
            label={t("config_page.transcription.mic_phrase_timeout.label")}
            desc={t("config_page.transcription.mic_phrase_timeout.desc")}
            selected_id={currentMicPhraseTimeout.data}
            list={genNumObjArray(31)}
            selectFunction={selectFunction}
            state={currentMicPhraseTimeout.state}
        />
    );
};
const MicMaxWords_Box = () => {
    const { t } = useI18n();
    const { currentMicMaxWords, setMicMaxWords } = useTranscription();

    const selectFunction = (selected_data) => {
        setMicMaxWords(selected_data.selected_id);
    };

    return (
        <DropdownMenuContainer
            dropdown_id="mic_max_phrase"
            label={t("config_page.transcription.mic_max_phrase.label")}
            desc={t("config_page.transcription.mic_max_phrase.desc")}
            selected_id={currentMicMaxWords.data}
            list={genNumObjArray(31)}
            selectFunction={selectFunction}
            state={currentMicMaxWords.state}
        />
    );
};

const MicWordFilter_Box = () => {
    const { t } = useI18n();

    return (
        <WordFilterContainer
            label={t("config_page.transcription.mic_word_filter.label")}
            desc={t("config_page.transcription.mic_word_filter.desc")}
        />
    );
};




const Speaker_Container = () => {
    const { t } = useI18n();
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
    const { t } = useI18n();
    const { currentSpeakerRecordTimeout, setSpeakerRecordTimeout } = useTranscription();

    const selectFunction = (selected_data) => {
        setSpeakerRecordTimeout(selected_data.selected_id);
    };

    return (
        <DropdownMenuContainer
            dropdown_id="speaker_record_timeout"
            desc={t("config_page.transcription.speaker_record_timeout.desc")}
            label={t("config_page.transcription.speaker_record_timeout.label")}
            selected_id={currentSpeakerRecordTimeout.data}
            list={genNumObjArray(31)}
            selectFunction={selectFunction}
            state={currentSpeakerRecordTimeout.state}
        />
    );
};
const SpeakerPhraseTimeout_Box = () => {
    const { t } = useI18n();
    const { currentSpeakerPhraseTimeout, setSpeakerPhraseTimeout } = useTranscription();

    const selectFunction = (selected_data) => {
        setSpeakerPhraseTimeout(selected_data.selected_id);
    };
    return (
        <DropdownMenuContainer
            dropdown_id="speaker_phrase_timeout"
            label={t("config_page.transcription.speaker_phrase_timeout.label")}
            desc={t("config_page.transcription.speaker_phrase_timeout.desc")}
            selected_id={currentSpeakerPhraseTimeout.data}
            list={genNumObjArray(31)}
            selectFunction={selectFunction}
            state={currentSpeakerPhraseTimeout.state}
        />
    );
};
const SpeakerMaxWords_Box = () => {
    const { t } = useI18n();
    const { currentSpeakerMaxWords, setSpeakerMaxWords } = useTranscription();

    const selectFunction = (selected_data) => {
        setSpeakerMaxWords(selected_data.selected_id);
    };

    return (
        <DropdownMenuContainer
            dropdown_id="speaker_max_phrase"
            label={t("config_page.transcription.speaker_max_phrase.label")}
            desc={t("config_page.transcription.speaker_max_phrase.desc")}
            selected_id={currentSpeakerMaxWords.data}
            list={genNumObjArray(61)}
            selectFunction={selectFunction}
            state={currentSpeakerMaxWords.state}
        />
    );
};



const TranscriptionEngine_Container = () => {
    const { t } = useI18n();
    return (
        <div>
            <SectionLabelComponent label={t("config_page.transcription.section_label_transcription_engines")} />
            <TranscriptionEngine_Box />
            <WhisperWeightType_Box />
            <TranscriptionComputeDevice_Box />
        </div>
    );
};

const TranscriptionEngine_Box = () => {
    const { t } = useI18n();
    const { currentSelectedTranscriptionEngine, setSelectedTranscriptionEngine } = useTranscription();

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
    const { t } = useI18n();
    const {
        currentWhisperWeightTypeStatus,
        pendingWhisperWeightTypeStatus,
        downloadWhisperWeightTypeStatus,
    } = useTranscription();
    const { currentSelectedWhisperWeightType, setSelectedWhisperWeightType } = useTranscription();

    const selectFunction = (id) => {
        setSelectedWhisperWeightType(id);
    };

    const downloadStartFunction = (id) => {
        pendingWhisperWeightTypeStatus(id);
        downloadWhisperWeightTypeStatus(id);
    };

    const new_labels = [
        { id: "tiny", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "tiny", capacity: "74.5MB"}) },
        { id: "base", label: t("config_page.transcription.whisper_weight_type.recommended_model_template", {model_name: "base", capacity: "141MB"}) },
        { id: "small", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "small", capacity: "463MB"}) },
        { id: "medium", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "medium", capacity: "1.42GB"}) },
        { id: "large-v1", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "large-v1", capacity: "2.87GB"}) },
        { id: "large-v2", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "large-v2", capacity: "2.87GB"}) },
        { id: "large-v3", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "large-v3", capacity: "2.87GB"}) },
        { id: "large-v3-turbo-int8", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "large-v3-turbo-int8", capacity: "794MB"}) },
        { id: "large-v3-turbo", label: t("config_page.transcription.whisper_weight_type.model_template", {model_name: "large-v3-turbo", capacity: "1.58GB"}) },
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

// Duplicate
const TranscriptionComputeDevice_Box = () => {
    const { t } = useI18n();
    const {
        currentSelectableTranscriptionComputeDeviceList,
        currentSelectedTranscriptionComputeDevice,
        setSelectedTranscriptionComputeDevice,
        currentSelectedTranscriptionComputeType,
        setSelectedTranscriptionComputeType,
    } = useTranscription();
    const { onMouseLeaveFunction } = useOnMouseLeaveDropdownMenu();
    const { currentIsBreakPoint } = useStore_IsBreakPoint();

    const list_for_ui = transformDeviceArray(currentSelectableTranscriptionComputeDeviceList.data);

    const target_index = findKeyByDeviceValue(currentSelectableTranscriptionComputeDeviceList.data, currentSelectedTranscriptionComputeDevice.data);

    const DEFAULT_ORDER = [
        "auto",
        "int8",
        "int8_bfloat16",
        "int8_float16",
        "int8_float32",
        "bfloat16",
        "float16",
        "int16",
        "float32"
    ];

    const sortComputeTypesArray = (compute_types_array = [], order) => {
        const src_set = new Set(compute_types_array);

        const from_order = order.filter((id) => src_set.has(id));

        const invalid_ids = compute_types_array.filter((id) => !order.includes(id));
        if (invalid_ids.length > 0) {
            console.error("[sortComputeTypesArray] Unsupported compute types ignored:", invalid_ids);
        }

        return from_order;
    };


    const buildSimpleLabels = (ordered_array = []) => {
        const n = ordered_array.length;
        if (n === 0) return {};

        const labels = {};

        ordered_array.forEach((id, idx) => {
            if (idx === 0 && id === "auto") {
                labels[id] = t("config_page.common.compute_device.type_template_auto");
                return;
            }

            if (idx === 1) {
                labels[id] = t(
                    "config_page.common.compute_device.type_template_low",
                    { type_name: id }
                );
                return;
            }

            if (idx === n - 1) {
                labels[id] = t(
                    "config_page.common.compute_device.type_template_high",
                    { type_name: id }
                );
                return;
            }

            labels[id] = id;
        });

        return labels;
    };


    const computeTypesArray = currentSelectableTranscriptionComputeDeviceList.data[target_index].compute_types;

    const ordered_array = sortComputeTypesArray(computeTypesArray, DEFAULT_ORDER);

    const new_compute_types_labels = buildSimpleLabels(ordered_array);

    const selectFunction_ComputeDevice = (selected_data) => {
        const target_obj = currentSelectableTranscriptionComputeDeviceList.data[selected_data.selected_id];
        setSelectedTranscriptionComputeDevice(target_obj);
    };

    const selectFunction_ComputeType = (selected_data) => {
        setSelectedTranscriptionComputeType(selected_data.selected_id);
    };

    const device_container_class = clsx(styles.device_container, {
        [styles.is_break_point]: currentIsBreakPoint.data,
    });

    const is_disabled_selector = currentSelectedTranscriptionComputeDevice.state === "pending" || currentSelectedTranscriptionComputeType.state === "pending";

    return (
        <div className={styles.mic_container}>
            <div className={device_container_class} onMouseLeave={onMouseLeaveFunction}>
                <LabelComponent
                    label={t("config_page.transcription.transcription_compute_device.label")}
                    desc={t("config_page.common.compute_device.desc")}
                />
                <div className={styles.device_contents}>

                    <div className={styles.device_dropdown_wrapper}>
                        <div className={styles.device_dropdown}>
                            <p className={styles.device_secondary_label}>{t("config_page.common.compute_device.label_device")}</p>
                            <DropdownMenu
                                dropdown_id="transcription_compute_device"
                                selected_id={target_index}
                                list={list_for_ui}
                                selectFunction={selectFunction_ComputeDevice}
                                state={currentSelectedTranscriptionComputeDevice.state}
                                style={{ maxWidth: "20rem", minWidth: "10rem" }}
                                is_disabled={is_disabled_selector}
                            />
                        </div>

                        <div className={styles.device_dropdown}>
                            <p className={styles.device_secondary_label}>{t("config_page.common.compute_device.label_type")}</p>
                            <DropdownMenu
                                dropdown_id="transcription_compute_type"
                                selected_id={currentSelectedTranscriptionComputeType.data}
                                list={new_compute_types_labels}
                                selectFunction={selectFunction_ComputeType}
                                state={currentSelectedTranscriptionComputeType.state}
                                is_disabled={is_disabled_selector}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
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





const Advanced_Container = () => {
    const { t } = useI18n();
    return (
        <div>
            <SectionLabelComponent label="Advanced Settings (Whisper Model)" />
            {/* <SectionLabelComponent label={t("config_page.transcription.section_label_transcription_engines")} /> */}
            <MicAvgLogprobContainer />
            <MicNoSpeechProbContainer />
            <SpeakerAvgLogprobContainer />
            <SpeakerNoSpeechProbContainer />
        </div>
    );
};

export const MicAvgLogprobContainer = () => {
    const { t } = useI18n();
    const { currentMicAvgLogprob, setMicAvgLogprob } = useTranscription();
    const [ui_mic_avg_logprob, setUiMicAvgLogprob] = useState(currentMicAvgLogprob.data);

    const onchangeFunction = (value) => {
        setUiMicAvgLogprob(value);
    };
    const onchangeCommittedFunction = (value) => {
        setMicAvgLogprob(value);
    };
    useEffect(() => {
        setUiMicAvgLogprob(currentMicAvgLogprob.data);
    }, [currentMicAvgLogprob.data]);

    // [Duplicated]
    const createMarks = (min, max) => {
        const marks = [];
        for (let value = min; value <= max; value += 0.2) {
            value = parseFloat(value.toFixed(1));
            marks.push({ value, label: `${value}` });
        }
        return marks;
    };

    const marks = createMarks(-2, 0);

    return (
        <SliderContainer
            label="Mic Avg Logprob"
            desc="Default: -0.8"
            min="-2"
            max="0"
            onchangeCommittedFunction={onchangeCommittedFunction}
            onchangeFunction={onchangeFunction}
            variable={ui_mic_avg_logprob}
            marks={marks}
            step={0.1}
            track={false}
        />
    );
};

export const MicNoSpeechProbContainer = () => {
    const { t } = useI18n();
    const { currentMicNoSpeechProb, setMicNoSpeechProb } = useTranscription();
    const [ui_mic_no_speech_prob, setUiMicNoSpeechProb] = useState(currentMicNoSpeechProb.data);

    const onchangeFunction = (value) => {
        setUiMicNoSpeechProb(value);
    };
    const onchangeCommittedFunction = (value) => {
        setMicNoSpeechProb(value);
    };
    useEffect(() => {
        setUiMicNoSpeechProb(currentMicNoSpeechProb.data);
    }, [currentMicNoSpeechProb.data]);

    // [Duplicated]
    const createMarks = (min, max) => {
        const marks = [];
        for (let value = min; value <= max; value += 0.1) {
            value = parseFloat(value.toFixed(1));
            marks.push({ value, label: `${value}` });
        }
        return marks;
    };

    const marks = createMarks(0, 1);

    return (
        <SliderContainer
            label="Mic No Speech Prob"
            desc="Default: 0.6"
            min="0"
            max="1"
            onchangeCommittedFunction={onchangeCommittedFunction}
            onchangeFunction={onchangeFunction}
            variable={ui_mic_no_speech_prob}
            marks={marks}
            step={0.1}
            track={false}
        />
    );
};

export const SpeakerAvgLogprobContainer = () => {
    const { t } = useI18n();
    const { currentSpeakerAvgLogprob, setSpeakerAvgLogprob } = useTranscription();
    const [ui_speaker_avg_logprob, setUiSpeakerAvgLogprob] = useState(currentSpeakerAvgLogprob.data);

    const onchangeFunction = (value) => {
        setUiSpeakerAvgLogprob(value);
    };
    const onchangeCommittedFunction = (value) => {
        setSpeakerAvgLogprob(value);
    };
    useEffect(() => {
        setUiSpeakerAvgLogprob(currentSpeakerAvgLogprob.data);
    }, [currentSpeakerAvgLogprob.data]);

    // [Duplicated]
    const createMarks = (min, max) => {
        const marks = [];
        for (let value = min; value <= max; value += 0.2) {
            value = parseFloat(value.toFixed(1));
            marks.push({ value, label: `${value}` });
        }
        return marks;
    };

    const marks = createMarks(-2, 0);

    return (
        <SliderContainer
            label="Speaker Avg Logprob"
            desc="Default: -0.8"
            min="-2"
            max="0"
            onchangeCommittedFunction={onchangeCommittedFunction}
            onchangeFunction={onchangeFunction}
            variable={ui_speaker_avg_logprob}
            marks={marks}
            step={0.1}
            track={false}
        />
    );
};

export const SpeakerNoSpeechProbContainer = () => {
    const { t } = useI18n();
    const { currentSpeakerNoSpeechProb, setSpeakerNoSpeechProb } = useTranscription();
    const [ui_speaker_no_speech_prob, setUiSpeakerNoSpeechProb] = useState(currentSpeakerNoSpeechProb.data);

    const onchangeFunction = (value) => {
        setUiSpeakerNoSpeechProb(value);
    };
    const onchangeCommittedFunction = (value) => {
        setSpeakerNoSpeechProb(value);
    };
    useEffect(() => {
        setUiSpeakerNoSpeechProb(currentSpeakerNoSpeechProb.data);
    }, [currentSpeakerNoSpeechProb.data]);

    // [Duplicated]
    const createMarks = (min, max) => {
        const marks = [];
        for (let value = min; value <= max; value += 0.1) {
            value = parseFloat(value.toFixed(1));
            marks.push({ value, label: `${value}` });
        }
        return marks;
    };

    const marks = createMarks(0, 1);

    return (
        <SliderContainer
            label="Speaker No Speech Prob"
            desc="Default: 0.6"
            min="0"
            max="1"
            onchangeCommittedFunction={onchangeCommittedFunction}
            onchangeFunction={onchangeFunction}
            variable={ui_speaker_no_speech_prob}
            marks={marks}
            step={0.1}
            track={false}
        />
    );
};