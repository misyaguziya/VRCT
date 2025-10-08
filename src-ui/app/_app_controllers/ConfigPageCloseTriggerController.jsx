import { useEffect } from "react";

import {
    useVolume,
    useIsOpenedConfigPage,
} from "@logics_common";

import {
    useMainFunction,
} from "@logics_main";

import { useHotkeys } from "@logics_configs";

import { useStore_MainFunctionsStateMemory } from "@store";

export const ConfigPageCloseTriggerController = () => {
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const {
        currentMainFunctionsStateMemory,
        updateMainFunctionsStateMemory,
    } = useStore_MainFunctionsStateMemory();

    const {
        currentTranslationStatus,
        setTranslation,
        pendingTranslationStatus,
        currentTranscriptionSendStatus,
        setTranscriptionSend,
        pendingTranscriptionSendStatus,
        currentTranscriptionReceiveStatus,
        setTranscriptionReceive,
        pendingTranscriptionReceiveStatus,
    } = useMainFunction();
    const {
        currentMicThresholdCheckStatus,
        volumeCheckStop_Mic,
        currentSpeakerThresholdCheckStatus,
        volumeCheckStop_Speaker,
    } = useVolume();

    const { registerShortcuts, unregisterAll } = useHotkeys();


    const memorizeLatestMainFunctionsState = () => {
        updateMainFunctionsStateMemory({
            translation: currentTranslationStatus.data,
            transcription_send: currentTranscriptionSendStatus.data,
            transcription_receive: currentTranscriptionReceiveStatus.data,
        });
    };

    const restoreMainFunctionState = () => {
        // First, set loading status all before waiting a backend process.
        if (currentMainFunctionsStateMemory.data.translation === true) pendingTranslationStatus();
        if (currentMainFunctionsStateMemory.data.transcription_send === true) pendingTranscriptionSendStatus();
        if (currentMainFunctionsStateMemory.data.transcription_receive === true) pendingTranscriptionReceiveStatus();

        // Then, restore them.
        if (currentMainFunctionsStateMemory.data.translation === true) setTranslation(true);
        if (currentMainFunctionsStateMemory.data.transcription_send === true) setTranscriptionSend(true);
        if (currentMainFunctionsStateMemory.data.transcription_receive === true) setTranscriptionReceive(true);
    };

    useEffect(() => {
        if (currentIsOpenedConfigPage.data === true) { // When config page is opened.
            memorizeLatestMainFunctionsState();
            unregisterAll();
            if (currentTranslationStatus.data === true) setTranslation(false);
            if (currentTranscriptionSendStatus.data === true) setTranscriptionSend(false);
            if (currentTranscriptionReceiveStatus.data === true) setTranscriptionReceive(false);
        } else if (currentIsOpenedConfigPage.data === false) { // When config page is closed.
            registerShortcuts();
            if (currentMicThresholdCheckStatus.data === true) volumeCheckStop_Mic();
            if (currentSpeakerThresholdCheckStatus.data === true) volumeCheckStop_Speaker();
            restoreMainFunctionState();
        }
    }, [currentIsOpenedConfigPage.data]);
    return null;
};