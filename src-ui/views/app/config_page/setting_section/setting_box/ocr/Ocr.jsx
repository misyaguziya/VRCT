import styles from "./Ocr.module.scss";

import { useOcr, useSaveButtonLogic } from "@logics_configs";

import {
    CheckboxContainer,
    SliderContainer,
    EntryWithSaveButtonContainer,
} from "../_templates/Templates";

import { SectionLabelComponent } from "../_components";

export const Ocr = () => {
    return (
        <div className={styles.container}>
            <div className={styles.section}>
                <SectionLabelComponent label="VRChat chat OCR" />
                <p className={styles.description}>
                    Capture VRChat chat bubbles on screen, run OCR, and route
                    the recognized text through the existing translation
                    pipeline. Output is mirrored to the main message log and
                    the SteamVR overlay; it is never sent to VRChat's OSC
                    chatbox.
                </p>
                <EnableOcrCaptureContainer />
            </div>

            <div className={styles.section}>
                <SectionLabelComponent label="Capture target" />
                <OcrWindowTitleContainer />
            </div>

            <div className={styles.section}>
                <SectionLabelComponent label="Language" />
                <OcrSourceLanguageContainer />
            </div>

            <div className={styles.section}>
                <SectionLabelComponent label="Performance" />
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
    const { currentEnableOcrCapture, toggleEnableOcrCapture } = useOcr();
    return (
        <CheckboxContainer
            label="Enable VRChat chat OCR"
            desc="Starts a background loop that captures the VRChat window (or the HMD mirror when SteamVR is running) and translates detected chat bubbles."
            variable={currentEnableOcrCapture}
            toggleFunction={toggleEnableOcrCapture}
        />
    );
};

const OcrWindowTitleContainer = () => {
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
            label="Window name"
            desc={"Substring match (case-insensitive) against visible window titles. Change this if you run a client whose window isn't titled 'VRChat' (e.g. a modified launcher)."}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentOcrWindowTitle.state}
            width="14rem"
        />
    );
};

const OcrSourceLanguageContainer = () => {
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
            label="OCR source language"
            desc={"Language the captured bubbles are written in. 'auto' loads Japanese + English readers. Set a VRCT language name (e.g. 'Japanese') to load only that reader. Applied on the next OCR start."}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentOcrSourceLanguage.state}
            width="14rem"
        />
    );
};

const OcrUseGpuContainer = () => {
    const { currentOcrUseGpu, toggleOcrUseGpu } = useOcr();
    return (
        <CheckboxContainer
            label="Use GPU for OCR"
            desc="Runs EasyOCR on CUDA when available. Falls back to CPU automatically if GPU init fails (e.g. VRAM tight after Whisper)."
            variable={currentOcrUseGpu}
            toggleFunction={toggleOcrUseGpu}
        />
    );
};

const OcrPollIntervalMsContainer = () => {
    const { currentOcrPollIntervalMs, setOcrPollIntervalMs } = useOcr();
    return (
        <SliderContainer
            label="Capture interval (ms)"
            desc="How often the OCR loop grabs a new frame. Lower = more responsive, higher CPU/GPU. Default: 750."
            variable={currentOcrPollIntervalMs.data}
            setterFunction={setOcrPollIntervalMs}
            min={200}
            max={3000}
            step={50}
        />
    );
};

const OcrMinConfidenceContainer = () => {
    const { currentOcrMinConfidence, setOcrMinConfidence } = useOcr();
    return (
        <SliderContainer
            label="Minimum OCR confidence"
            desc="Words below this EasyOCR confidence score are discarded. Raise to reduce false positives; lower to catch faint bubbles. Default: 0.55."
            variable={currentOcrMinConfidence.data}
            setterFunction={setOcrMinConfidence}
            min={0.2}
            max={0.95}
            step={0.05}
        />
    );
};

const OcrBubbleMinTextLengthContainer = () => {
    const { currentOcrBubbleMinTextLength, setOcrBubbleMinTextLength } = useOcr();
    return (
        <SliderContainer
            label="Minimum text length"
            desc="Bubbles with fewer characters than this are ignored. Default: 2."
            variable={currentOcrBubbleMinTextLength.data}
            setterFunction={setOcrBubbleMinTextLength}
            min={1}
            max={20}
            step={1}
        />
    );
};

const OcrDedupCooldownSecContainer = () => {
    const { currentOcrDedupCooldownSec, setOcrDedupCooldownSec } = useOcr();
    return (
        <SliderContainer
            label="Dedup cooldown (seconds)"
            desc="How long the same text stays suppressed after being translated once. VRChat bubbles linger ~7 s so 8 s is a good default."
            variable={currentOcrDedupCooldownSec.data}
            setterFunction={setOcrDedupCooldownSec}
            min={1}
            max={60}
            step={1}
        />
    );
};
