import { useI18n } from "@useI18n";
import styles from "./Ocr.module.scss";

import { useOcr } from "@logics_configs";
import { useSaveButtonLogic } from "@logics_configs";

import {
    SwitchBoxContainer,
    DropdownMenuContainer,
    EntryWithSaveButtonContainer,
    SliderContainer,
} from "../_templates/Templates";

import { SectionLabelComponent } from "../_components";

export const Ocr = () => {
    return (
        <div className={styles.container}>
            <Main_Container />
            <Advanced_Container />
        </div>
    );
};


const Main_Container = () => {
    const { t } = useI18n();
    return (
        <div>
            <SectionLabelComponent label={t("config_page.ocr.section_title")} desc={t("config_page.ocr.section_desc")} />
            <EnableOcrCapture_Box />
            <OcrSourceLanguage_Box />
        </div>
    );
};

const EnableOcrCapture_Box = () => {
    const { t } = useI18n();
    const { currentEnableOcrCapture, toggleEnableOcrCapture } = useOcr();

    return (
        <SwitchBoxContainer
            label={t("config_page.ocr.enable_ocr_capture.label")}
            desc={t("config_page.ocr.enable_ocr_capture.desc")}
            variable={currentEnableOcrCapture}
            toggleFunction={toggleEnableOcrCapture}
        />
    );
};

const OcrSourceLanguage_Box = () => {
    const { t } = useI18n();
    const { currentSelectableOcrSourceLanguageList, currentOcrSourceLanguage, setOcrSourceLanguage } = useOcr();

    const selectFunction = (selected_data) => {
        setOcrSourceLanguage(selected_data.selected_id);
    };

    return (
        <DropdownMenuContainer
            dropdown_id="ocr_source_language"
            label={t("config_page.ocr.source_language.label")}
            desc={t("config_page.ocr.source_language.desc")}
            selected_id={currentOcrSourceLanguage.data}
            list={currentSelectableOcrSourceLanguageList.data}
            selectFunction={selectFunction}
            state={currentOcrSourceLanguage.state}
            remove_border_bottom={true}
        />
    );
};


const Advanced_Container = () => {
    return (
        <>
            <CaptureTarget_Container />
            <Performance_Container />
        </>
    );
};

const CaptureTarget_Container = () => {
    const { t } = useI18n();
    return (
        <div>
            <SectionLabelComponent label={t("config_page.ocr.capture_target")} />
            <OcrWindowTitle_Box />
        </div>
    );
};

const Performance_Container = () => {
    const { t } = useI18n();
    return (
        <div>
            <SectionLabelComponent label={t("config_page.ocr.performance")} />
            <OcrPollIntervalMs_Box />
            <OcrMinConfidence_Box />
            <OcrBubbleMinTextLength_Box />
        </div>
    );
};

const OcrWindowTitle_Box = () => {
    const { t } = useI18n();
    const { currentOcrWindowTitle, setOcrWindowTitle } = useOcr();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentOcrWindowTitle.data,
        state: currentOcrWindowTitle.state,
        setFunction: setOcrWindowTitle,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.ocr.window_title.label")}
            desc={t("config_page.ocr.window_title.desc")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentOcrWindowTitle.state}
            width="16rem"
            remove_border_bottom={true}
        />
    );
};

const OcrPollIntervalMs_Box = () => {
    const { t } = useI18n();
    const { currentOcrPollIntervalMs, setOcrPollIntervalMs } = useOcr();

    return (
        <SliderContainer
            label={t("config_page.ocr.poll_interval_ms.label")}
            desc={t("config_page.ocr.poll_interval_ms.desc")}
            variable={currentOcrPollIntervalMs.data}
            setterFunction={setOcrPollIntervalMs}
            min={100}
            max={5000}
            step={50}
            marks_step={500}
            valueLabelFormat={(v) => `${v} ms`}
        />
    );
};

const OcrMinConfidence_Box = () => {
    const { t } = useI18n();
    const { currentOcrMinConfidence, setOcrMinConfidence } = useOcr();

    return (
        <SliderContainer
            label={t("config_page.ocr.min_confidence.label")}
            desc={t("config_page.ocr.min_confidence.desc")}
            variable={currentOcrMinConfidence.data}
            setterFunction={setOcrMinConfidence}
            min={0.1}
            max={0.99}
            step={0.01}
            marks_step={0.1}
        />
    );
};

const OcrBubbleMinTextLength_Box = () => {
    const { t } = useI18n();
    const { currentOcrBubbleMinTextLength, setOcrBubbleMinTextLength } = useOcr();

    return (
        <SliderContainer
            label={t("config_page.ocr.bubble_min_text_length.label")}
            desc={t("config_page.ocr.bubble_min_text_length.desc")}
            variable={currentOcrBubbleMinTextLength.data}
            setterFunction={setOcrBubbleMinTextLength}
            min={1}
            max={50}
            step={1}
            marks_step={5}
            remove_border_bottom={true}
        />
    );
};
