import { useI18n } from "@useI18n";
import clsx from "clsx";
import styles from "./MainFunctionSwitch.module.scss";
import TranslationSvg from "@images/translation.svg?react";
import MicSvg from "@images/mic.svg?react";
import HeadphonesSvg from "@images/headphones.svg?react";
import ChatTranscribeSvg from "@images/chat_transcribe.svg?react";
import {
    useIsMainPageCompactMode,
    useMainFunction,
} from "@logics_main";
import { ToggleSwitch } from "@common_components";

export const MainFunctionSwitch = () => {
    const { t } = useI18n();

    const {
        toggleTranslation, currentTranslationStatus,
        toggleTranscriptionSend, currentTranscriptionSendStatus,
        toggleTranscriptionReceive, currentTranscriptionReceiveStatus,
        toggleOcrCapture, currentOcrCaptureStatus,
    } = useMainFunction();


    const switch_items = [
        {
            switch_id: "translation",
            label: t("main_page.translation"),
            SvgComponent: TranslationSvg,
            currentState: currentTranslationStatus,
            toggleFunction: toggleTranslation,
        },
        {
            switch_id: "transcription_send",
            label: t("main_page.transcription_send"),
            SvgComponent: MicSvg,
            currentState: currentTranscriptionSendStatus,
            toggleFunction: toggleTranscriptionSend,
        },
        {
            switch_id: "transcription_receive",
            label: t("main_page.transcription_receive"),
            SvgComponent: HeadphonesSvg,
            currentState: currentTranscriptionReceiveStatus,
            toggleFunction: toggleTranscriptionReceive,
        },
        {
            switch_id: "ocr",
            label: t("main_page.ocr"),
            SvgComponent: ChatTranscribeSvg,
            currentState: currentOcrCaptureStatus,
            toggleFunction: toggleOcrCapture,
        },
    ];

    return (
        <div className={styles.container}>
            {switch_items.map(item => (
                <SwitchContainer
                    key={item.switch_id}
                    switch_id={item.switch_id}
                    switchLabel={item.label}
                    currentState={item.currentState}
                    toggleFunction={item.toggleFunction}
                    SvgComponent={item.SvgComponent}
                >
                </SwitchContainer>
            ))}
        </div>
    );
};

export const SwitchContainer = ({ switchLabel, switch_id, children, currentState, toggleFunction, SvgComponent }) => {
    const { currentIsMainPageCompactMode } = useIsMainPageCompactMode();

    const getClassNames = (baseClass) => clsx(baseClass, {
        [styles.is_compact_mode]: currentIsMainPageCompactMode.data,
        [styles.is_active]: (currentState.data === true),
        [styles.is_pending]: (currentState.state === "pending"),
    });

    return (
        <div
            className={getClassNames(styles.switch_container)}
            onClick={toggleFunction}
        >
            <div className={styles.label_wrapper}>
                <SvgComponent className={getClassNames(styles.switch_svg)} />
                <p className={getClassNames(styles.switch_label)}>{switchLabel}</p>
                {children}
            </div>

            <ToggleSwitch
                isActive={currentState.data === true}
                isPending={currentState.state === "pending"}
                className={getClassNames(styles.toggle_control)}
            />

            <div className={getClassNames(styles.switch_indicator)}></div>
            {(currentState.state === "pending") && (
                <span className={styles.loader}></span>
            )}
        </div>
    );
};