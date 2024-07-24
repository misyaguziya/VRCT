import { useTranslation } from "react-i18next";
import clsx from "clsx";
import styles from "./MainFunctionSwitch.module.scss";
import TranslationSvg from "@images/translation.svg?react";
import MicSvg from "@images/mic.svg?react";
import HeadphonesSvg from "@images/headphones.svg?react";
import ForegroundSvg from "@images/foreground.svg?react";
import { useIsCompactMode } from "@store";

import { useMainFunction } from "@logics/useMainFunction";

export const MainFunctionSwitch = () => {
    const { t } = useTranslation();

    const {
        toggleTranslation, currentState_Translation,
        toggleTranscriptionSend, currentState_TranscriptionSend,
        toggleTranscriptionReceive, currentState_TranscriptionReceive,
        toggleForeground, currentState_Foreground,
    } = useMainFunction();


    const switch_items = [
        {
            switch_id: "translation",
            label: t("main_window.translation"),
            SvgComponent: TranslationSvg,
            currentState: currentState_Translation,
            toggleFunction: toggleTranslation,
        },
        {
            switch_id: "transcription_send",
            label: t("main_window.transcription_send"),
            SvgComponent: MicSvg,
            currentState: currentState_TranscriptionSend,
            toggleFunction: toggleTranscriptionSend,
        },
        {
            switch_id: "transcription_receive",
            label: t("main_window.transcription_receive"),
            SvgComponent: HeadphonesSvg,
            currentState: currentState_TranscriptionReceive,
            toggleFunction: toggleTranscriptionReceive,
        },
        {
            switch_id: "foreground",
            label: t("main_window.foreground"),
            SvgComponent: ForegroundSvg,
            currentState: currentState_Foreground,
            toggleFunction: toggleForeground,
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

import { useState } from "react";

export const SwitchContainer = ({ switchLabel, switch_id, children, currentState, toggleFunction, SvgComponent }) => {
    const [is_hovered, setIsHovered] = useState(false);
    const [is_mouse_down, setIsMouseDown] = useState(false);

    const { currentIsCompactMode } = useIsCompactMode();

    const getClassNames = (baseClass) => clsx(baseClass, {
        [styles.is_compact_mode]: currentIsCompactMode,
        [styles.is_active]: (currentState.data === true),
        [styles.is_loading]: (currentState.state === "loading"),
        [styles.is_hovered]: is_hovered,
        [styles.is_mouse_down]: is_mouse_down,
    });

    const onMouseEnter = () => setIsHovered(true);
    const onMouseLeave = () => setIsHovered(false);
    const onMouseDown = () => setIsMouseDown(true);
    const onMouseUp = () => setIsMouseDown(false);

    return (
        <div className={getClassNames(styles.switch_container)}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        onMouseDown={onMouseDown}
        onMouseUp={onMouseUp}
        onClick={toggleFunction}
        >
            <div className={styles.label_wrapper}>
                <SvgComponent className={getClassNames(styles.switch_svg)} />
                <p className={getClassNames(styles.switch_label)}>{switchLabel}</p>
                {children}
            </div>

            <div className={getClassNames(styles.toggle_control)}>
                <span className={getClassNames(styles.control)}></span>
            </div>

            <div className={getClassNames(styles.switch_indicator)}></div>
            {(currentState.state === "loading")
                ? <span className={styles.loader}></span>
                : null
            }
        </div>
    );
};