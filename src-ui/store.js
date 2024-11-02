import {
    atom,
    useAtomValue,
    useSetAtom
} from "jotai";

import {
    translator_status,
    generateTestData,
} from "@data";

export const store = {
    backend_subprocess: null,
    config_page: null,
    log_box_ref: null,
};

const generatePropertyNames = (base_name) => ({
    error: `error${base_name}`,
    pending: `pending${base_name}`,
    current: `current${base_name}`,
    update: `update${base_name}`,
    updatePart: `updatePart${base_name}`,
    async_update: `asyncUpdate${base_name}`,
    add: `add${base_name}`,
    async_add: `asyncAdd${base_name}`,
});


const createAtomWithHook = (initialValue, base_name, options) => {
    const property_names = generatePropertyNames(base_name);
    const atomInstance = atom({
        state: (options?.is_state_ok) ? "ok" : "pending",
        data: initialValue,
    });

    const useHook = () => {
        const currentAtom = useAtomValue(atomInstance);
        const setAtom = useSetAtom(atomInstance);

        const pendingAtom = () => {
            setAtom((old_value) => {
                let new_value = {
                    state: "pending",
                    data: old_value.data,
                };
                return new_value;
            });
        };

        const updateAtom = (payload) => {
            setAtom((currentValue) => {
                if (typeof payload === "function") {
                    const updated_data = payload(currentValue);
                    return {
                        state: "ok",
                        data: updated_data,
                    };
                } else {
                    return {
                        state: "ok",
                        data: payload,
                    };
                }
            });
        };

        const errorAtom = () => {
            setAtom((old_value) => {
                let new_value = {
                    state: "error",
                    data: old_value.data,
                };
                return new_value;
            });
        };

        const addAtom = (value) => {
            setAtom((old_value) => {
                return {
                    state: "ok",
                    data: [...old_value.data, value],
                };
            });
        };

        return {
            [property_names.error]: errorAtom,
            [property_names.pending]: pendingAtom,
            [property_names.current]: currentAtom,
            [property_names.update]: updateAtom,
            [property_names.add]: addAtom,
        };
    };

    return { atomInstance, useHook };
};


// Common
export const { atomInstance: Atom_IsOpenedConfigPage, useHook: useStore_IsOpenedConfigPage } = createAtomWithHook(false, "IsOpenedConfigPage");
export const { atomInstance: Atom_MainFunctionsStateMemory, useHook: useStore_MainFunctionsStateMemory } = createAtomWithHook({
    transcription_send: false,
    transcription_receive: false,
}, "MainFunctionsStateMemory");
export const { atomInstance: Atom_OpenedQuickSetting, useHook: useStore_OpenedQuickSetting } = createAtomWithHook("", "OpenedQuickSetting");

// Main Page
// Functions
export const { atomInstance: Atom_TranslationStatus, useHook: useStore_TranslationStatus } = createAtomWithHook(false, "TranslationStatus", {is_state_ok: true});
export const { atomInstance: Atom_TranscriptionSendStatus, useHook: useStore_TranscriptionSendStatus } = createAtomWithHook(false, "TranscriptionSendStatus", {is_state_ok: true});
export const { atomInstance: Atom_TranscriptionReceiveStatus, useHook: useStore_TranscriptionReceiveStatus } = createAtomWithHook(false, "TranscriptionReceiveStatus", {is_state_ok: true});
export const { atomInstance: Atom_ForegroundStatus, useHook: useStore_ForegroundStatus } = createAtomWithHook(false, "ForegroundStatus", {is_state_ok: true});

export const { atomInstance: Atom_MessageLogs, useHook: useStore_MessageLogs } = createAtomWithHook(generateTestData(20), "MessageLogs");

export const { atomInstance: Atom_SelectableLanguageList, useHook: useStore_SelectableLanguageList } = createAtomWithHook([], "SelectableLanguageList");

export const { atomInstance: Atom_SelectedPresetTabNumber, useHook: useStore_SelectedPresetTabNumber } = createAtomWithHook("", "SelectedPresetTabNumber");
export const { atomInstance: Atom_EnableMultiTranslation, useHook: useStore_EnableMultiTranslation } = createAtomWithHook(false, "EnableMultiTranslation");
export const { atomInstance: Atom_SelectedYourLanguages, useHook: useStore_SelectedYourLanguages } = createAtomWithHook({}, "SelectedYourLanguages");
export const { atomInstance: Atom_SelectedTargetLanguages, useHook: useStore_SelectedTargetLanguages } = createAtomWithHook({}, "SelectedTargetLanguages");


export const { atomInstance: Atom_TranslationEngines, useHook: useStore_TranslationEngines } = createAtomWithHook(translator_status, "TranslationEngines");
export const { atomInstance: Atom_SelectedTranslationEngines, useHook: useStore_SelectedTranslationEngines } = createAtomWithHook({
    engines: {1:"", 2:"", 3:""},
    weight_type: "small",
}, "SelectedTranslationEngines");


// Designs
export const { atomInstance: Atom_IsMainPageCompactMode, useHook: useStore_IsMainPageCompactMode } = createAtomWithHook(false, "IsMainPageCompactMode");
export const { atomInstance: Atom_MessageInputBoxRatio, useHook: useStore_MessageInputBoxRatio } = createAtomWithHook(20, "MessageInputBoxRatio");
export const { atomInstance: Atom_IsOpenedLanguageSelector, useHook: useStore_IsOpenedLanguageSelector } = createAtomWithHook(
    { your_language: false, target_language: false },
    "IsOpenedLanguageSelector"
);


// Config Page
// Common
export const { atomInstance: Atom_SoftwareVersion, useHook: useStore_SoftwareVersion } = createAtomWithHook("-", "SoftwareVersion");
export const { atomInstance: Atom_SelectedConfigTabId, useHook: useStore_SelectedConfigTabId } = createAtomWithHook("device", "SelectedConfigTabId");

// Designs
export const { atomInstance: Atom_IsOpenedDropdownMenu, useHook: useStore_IsOpenedDropdownMenu } = createAtomWithHook("", "IsOpenedDropdownMenu");

// Device
export const { atomInstance: Atom_EnableAutoMicSelect, useHook: useStore_EnableAutoMicSelect } = createAtomWithHook(true, "EnableAutoMicSelect");
export const { atomInstance: Atom_EnableAutoSpeakerSelect, useHook: useStore_EnableAutoSpeakerSelect } = createAtomWithHook(true, "EnableAutoSpeakerSelect");

export const { atomInstance: Atom_MicHostList, useHook: useStore_MicHostList } = createAtomWithHook({}, "MicHostList");
export const { atomInstance: Atom_SelectedMicHost, useHook: useStore_SelectedMicHost } = createAtomWithHook("Nothing Selected", "SelectedMicHost");
export const { atomInstance: Atom_MicDeviceList, useHook: useStore_MicDeviceList } = createAtomWithHook({}, "MicDeviceList");
export const { atomInstance: Atom_SelectedMicDevice, useHook: useStore_SelectedMicDevice } = createAtomWithHook("Nothing Selected", "SelectedMicDevice");

export const { atomInstance: Atom_SpeakerDeviceList, useHook: useStore_SpeakerDeviceList } = createAtomWithHook({}, "SpeakerDeviceList");
export const { atomInstance: Atom_SelectedSpeakerDevice, useHook: useStore_SelectedSpeakerDevice } = createAtomWithHook("Nothing Selected", "SelectedSpeakerDevice");

export const { atomInstance: Atom_MicVolume, useHook: useStore_MicVolume } = createAtomWithHook(0, "MicVolume");
export const { atomInstance: Atom_SpeakerVolume, useHook: useStore_SpeakerVolume } = createAtomWithHook(0, "SpeakerVolume");

export const { atomInstance: Atom_MicThresholdCheckStatus, useHook: useStore_MicThresholdCheckStatus } = createAtomWithHook(false, "MicThresholdCheckStatus", {is_state_ok: true});
export const { atomInstance: Atom_SpeakerThresholdCheckStatus, useHook: useStore_SpeakerThresholdCheckStatus } = createAtomWithHook(false, "SpeakerThresholdCheckStatus", {is_state_ok: true});

export const { atomInstance: Atom_MicThreshold, useHook: useStore_MicThreshold } = createAtomWithHook(0, "MicThreshold");
export const { atomInstance: Atom_SpeakerThreshold, useHook: useStore_SpeakerThreshold } = createAtomWithHook(0, "SpeakerThreshold");

export const { atomInstance: Atom_EnableAutomaticMicThreshold, useHook: useStore_EnableAutomaticMicThreshold } = createAtomWithHook(false, "EnableAutomaticMicThreshold");
export const { atomInstance: Atom_EnableAutomaticSpeakerThreshold, useHook: useStore_EnableAutomaticSpeakerThreshold } = createAtomWithHook(false, "EnableAutomaticSpeakerThreshold");


// Appearance
export const { atomInstance: Atom_UiLanguage, useHook: useStore_UiLanguage } = createAtomWithHook("en", "UiLanguage");
export const { atomInstance: Atom_UiScaling, useHook: useStore_UiScaling } = createAtomWithHook(100, "UiScaling");
export const { atomInstance: Atom_MessageLogUiScaling, useHook: useStore_MessageLogUiScaling } = createAtomWithHook(100, "MessageLogUiScaling");
export const { atomInstance: Atom_SendMessageButtonType, useHook: useStore_SendMessageButtonType } = createAtomWithHook("show", "SendMessageButtonType");
export const { atomInstance: Atom_SelectedFontFamily, useHook: useStore_SelectedFontFamily } = createAtomWithHook("Yu Gothic UI", "SelectedFontFamily");
export const { atomInstance: Atom_SelectableFontFamilyList, useHook: useStore_SelectableFontFamilyList } = createAtomWithHook({}, "SelectableFontFamilyList");
export const { atomInstance: Atom_Transparency, useHook: useStore_Transparency } = createAtomWithHook(100, "Transparency");


export const { atomInstance: Atom_IsOpenedMicWordFilterList, useHook: useStore_IsOpenedMicWordFilterList } = createAtomWithHook(false, "IsOpenedMicWordFilterList");
export const { atomInstance: Atom_MicWordFilterList, useHook: useStore_MicWordFilterList } = createAtomWithHook([], "MicWordFilterList");

// Translation
export const { atomInstance: Atom_DeepLAuthKey, useHook: useStore_DeepLAuthKey } = createAtomWithHook(null, "DeepLAuthKey");

// Transcription
export const { atomInstance: Atom_MicRecordTimeout, useHook: useStore_MicRecordTimeout } = createAtomWithHook(0, "MicRecordTimeout");
export const { atomInstance: Atom_MicPhraseTimeout, useHook: useStore_MicPhraseTimeout } = createAtomWithHook(0, "MicPhraseTimeout");
export const { atomInstance: Atom_MicMaxWords, useHook: useStore_MicMaxWords } = createAtomWithHook(0, "MicMaxWords");

export const { atomInstance: Atom_SpeakerRecordTimeout, useHook: useStore_SpeakerRecordTimeout } = createAtomWithHook(0, "SpeakerRecordTimeout");
export const { atomInstance: Atom_SpeakerPhraseTimeout, useHook: useStore_SpeakerPhraseTimeout } = createAtomWithHook(0, "SpeakerPhraseTimeout");
export const { atomInstance: Atom_SpeakerMaxWords, useHook: useStore_SpeakerMaxWords } = createAtomWithHook(0, "SpeakerMaxWords");

// VR
export const { atomInstance: Atom_OverlaySettings, useHook: useStore_OverlaySettings } = createAtomWithHook({
    opacity: 1.0,
    ui_scaling: 1.0,
}, "OverlaySettings");
export const { atomInstance: Atom_OverlaySmallLogSettings, useHook: useStore_OverlaySmallLogSettings } = createAtomWithHook({
    x_pos: 0.0,
    y_pos: 0.0,
    z_pos: 0.0,
    x_rotation: 0.0,
    y_rotation: 0.0,
    z_rotation: 0.0,
    display_duration: 5,
    fadeout_duration: 2,
}, "OverlaySmallLogSettings");
export const { atomInstance: Atom_IsEnabledOverlaySmallLog, useHook: useStore_IsEnabledOverlaySmallLog } = createAtomWithHook(false, "IsEnabledOverlaySmallLog");

// Others
export const { atomInstance: Atom_EnableAutoClearMessageInputBox, useHook: useStore_EnableAutoClearMessageInputBox } = createAtomWithHook(true, "EnableAutoClearMessageInputBox");
export const { atomInstance: Atom_EnableSendOnlyTranslatedMessages, useHook: useStore_EnableSendOnlyTranslatedMessages } = createAtomWithHook(false, "EnableSendOnlyTranslatedMessages");
export const { atomInstance: Atom_EnableAutoExportMessageLogs, useHook: useStore_EnableAutoExportMessageLogs } = createAtomWithHook(false, "EnableAutoExportMessageLogs");
export const { atomInstance: Atom_EnableVrcMicMuteSync, useHook: useStore_EnableVrcMicMuteSync } = createAtomWithHook(false, "EnableVrcMicMuteSync");
export const { atomInstance: Atom_EnableSendMessageToVrc, useHook: useStore_EnableSendMessageToVrc } = createAtomWithHook(true, "EnableSendMessageToVrc");

// Advanced Settings
export const { atomInstance: Atom_OscIpAddress, useHook: useStore_OscIpAddress } = createAtomWithHook("127.0.0.1", "OscIpAddress");
export const { atomInstance: Atom_OscPort, useHook: useStore_OscPort } = createAtomWithHook("9000", "OscPort");



export const { atomInstance: Atom_IsOpenedTranslatorSelector, useHook: useStore_IsOpenedTranslatorSelector } = createAtomWithHook(false, "IsOpenedTranslatorSelector");

export const { atomInstance: Atom_VrctPosterIndex, useHook: useStore_VrctPosterIndex } = createAtomWithHook(0, "VrctPosterIndex");
export const { atomInstance: Atom_PosterShowcaseWorldPageIndex, useHook: useStore_PosterShowcaseWorldPageIndex } = createAtomWithHook(0, "PosterShowcaseWorldPageIndex");