import styles from "./Ocr.module.scss";

import { useI18n } from "@useI18n";
import { useOcr, useSaveButtonLogic } from "@logics_configs";

import {
    CheckboxContainer,
    SliderContainer,
    EntryWithSaveButtonContainer,
} from "../_templates/Templates";

import { SectionLabelComponent } from "../_components";

export const Ocr = () => {
    const { t } = useI18n();
    return (
        <div className={styles.container}>
            <div className={styles.section}>
                <SectionLabelComponent label={t("config_page.ocr.section_title")} />
                <p className={styles.description}>
                    {t("config_page.ocr.section_desc")}
                </p>
                <EnableOcrCaptureContainer />
            </div>

            <div className={styles.section}>
                <SectionLabelComponent label={t("config_page.ocr.capture_target")} />
                <OcrWindowTitleContainer />
            </div>

            <div className={styles.section}>
                <SectionLabelComponent label={t("config_page.ocr.language")} />
                <OcrSourceLanguageContainer />
            </div>

            <div className={styles.section}>
                <SectionLabelComponent label={t("config_page.ocr.performance")} />
                <OcrUseGpuContainer />
                <OcrPollIntervalMsContainer />
                <OcrMinConfidenceContainer />
                <OcrBubbleMinTextLengthContainer />
                <OcrDedupCooldownSecContainer />
            </div>
        </div>
    );
};

const EnableOcrCaptureContainer = () => {
    const { t } = useI18n();
    const { currentEnableOcrCapture, toggleEnableOcrCapture } = useOcr();
    return (
        <CheckboxContainer
            label={t("config_page.ocr.enable_ocr_capture.label")}
            desc={t("config_page.ocr.enable_ocr_capture.desc")}
            variable={currentEnableOcrCapture}
            toggleFunction={toggleEnableOcrCapture}
        />
    );
};

const OcrWindowTitleContainer = () => {
    const { t } = useI18n();
    const { currentOcrWindowTitle, setOcrWindowTitle } = useOcr();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentOcrWindowTitle.data,
        state: currentOcrWindowTitle.state,
        setFunction: setOcrWindowTitle,
        // useSaveButtonLogic calls deleteFunction() on an empty field; there is
        // no delete endpoint here, so clearing it restores the default title.
        deleteFunction: () => setOcrWindowTitle("VRChat"),
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.ocr.window_title.label")}
            desc={t("config_page.ocr.window_title.desc")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentOcrWindowTitle.state}
            width="14rem"
        />
    );
};

const OcrSourceLanguageContainer = () => {
    const { t } = useI18n();
    const { currentOcrSourceLanguage, setOcrSourceLanguage } = useOcr();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentOcrSourceLanguage.data,
        state: currentOcrSourceLanguage.state,
        setFunction: setOcrSourceLanguage,
        // useSaveButtonLogic calls deleteFunction() on an empty field; this
        // setting has no delete endpoint, so clearing it means "back to auto".
        deleteFunction: () => setOcrSourceLanguage("auto"),
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.ocr.source_language.label")}
            desc={t("config_page.ocr.source_language.desc")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentOcrSourceLanguage.state}
            width="14rem"
        />
    );
};

const OcrUseGpuContainer = () => {
    const { t } = useI18n();
    const { currentOcrUseGpu, toggleOcrUseGpu } = useOcr();
    return (
        <CheckboxContainer
            label={t("config_page.ocr.use_gpu.label")}
            desc={t("config_page.ocr.use_gpu.desc")}
            variable={currentOcrUseGpu}
            toggleFunction={toggleOcrUseGpu}
        />
    );
};

const OcrPollIntervalMsContainer = () => {
    const { t } = useI18n();
    const { currentOcrPollIntervalMs, setOcrPollIntervalMs } = useOcr();
    return (
        <SliderContainer
            label={t("config_page.ocr.poll_interval_ms.label")}
            desc={t("config_page.ocr.poll_interval_ms.desc")}
            variable={currentOcrPollIntervalMs.data}
            setterFunction={setOcrPollIntervalMs}
            min={200}
            max={3000}
            step={50}
        />
    );
};

const OcrMinConfidenceContainer = () => {
    const { t } = useI18n();
    const { currentOcrMinConfidence, setOcrMinConfidence } = useOcr();
    return (
        <SliderContainer
            label={t("config_page.ocr.min_confidence.label")}
            desc={t("config_page.ocr.min_confidence.desc")}
            variable={currentOcrMinConfidence.data}
            setterFunction={setOcrMinConfidence}
            min={0.2}
            max={0.95}
            step={0.05}
        />
    );
};

const OcrBubbleMinTextLengthContainer = () => {
    const { t } = useI18n();
    const { currentOcrBubbleMinTextLength, setOcrBubbleMinTextLength } = useOcr();
    return (
        <SliderContainer
            label={t("config_page.ocr.bubble_min_text_length.label")}
            desc={t("config_page.ocr.bubble_min_text_length.desc")}
            variable={currentOcrBubbleMinTextLength.data}
            setterFunction={setOcrBubbleMinTextLength}
            min={1}
            max={20}
            step={1}
        />
    );
};

const OcrDedupCooldownSecContainer = () => {
    const { t } = useI18n();
    const { currentOcrDedupCooldownSec, setOcrDedupCooldownSec } = useOcr();
    return (
        <SliderContainer
            label={t("config_page.ocr.dedup_cooldown_sec.label")}
            desc={t("config_page.ocr.dedup_cooldown_sec.desc")}
            variable={currentOcrDedupCooldownSec.data}
            setterFunction={setOcrDedupCooldownSec}
            min={1}
            max={60}
            step={1}
        />
    );
};
