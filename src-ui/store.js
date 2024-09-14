import {
    atom,
    useAtomValue,
    useSetAtom
} from "jotai";

import {
    translator_list,
    generateTestData,
    word_filter_list,
} from "@data";

export const store = {
    backend_subprocess: null,
    config_page: null,
    log_box_ref: null,
};

const generatePropertyNames = (base_ame) => ({
    current: `current${base_ame}`,
    update: `update${base_ame}`,
    async_update: `asyncUpdate${base_ame}`,
    add: `add${base_ame}`,
    async_add: `asyncAdd${base_ame}`,
});

const createAtomWithHook = (initialValue, base_ame) => {
    const property_names = generatePropertyNames(base_ame);
    const atomInstance = atom(initialValue);

    const useHook = () => {
        const currentAtom = useAtomValue(atomInstance);
        const setAtom = useSetAtom(atomInstance);

        const updateAtom = (value) => {
            setAtom(value);
        };

        const addAtom = (value) => {
            setAtom((old_value) => [...old_value, value]);
        };

        return {
            [property_names.current]: currentAtom,
            [property_names.update]: updateAtom,
            [property_names.add]: addAtom,
        };
    };

    return { atomInstance, useHook };
};

import { loadable } from "jotai/utils";
const createAsyncAtomWithHook = (initialValue, base_ame) => {
    const property_names = generatePropertyNames(base_ame);
    const atomInstance = atom(initialValue);
    const asyncAtom = atom(async (get) => get(atomInstance));
    const loadableAtom = loadable(asyncAtom);

    const useHook = () => {
        const asyncCurrentAtom = useAtomValue(loadableAtom);
        const setAtom = useSetAtom(atomInstance);

        const updateAtom = (value) => {
            setAtom(value);
        };

        const asyncSetAtom = useSetAtom(atom(null, async (get, set, payloadAsyncFunc, ...args) => {
            set(atomInstance, payloadAsyncFunc(...args));
        }));

        const asyncUpdateAtom = async (asyncFunction, ...args) => {
            asyncSetAtom(asyncFunction, ...args);
        };

        const addAtom = (value) => {
            setAtom((old_value) => [...old_value, value]);
        };

        const asyncAddAtom = useSetAtom(atom(null, async (get, set, payloadAsyncFunc, ...args) => {
            const old_value = await get(atomInstance);
            set(atomInstance, payloadAsyncFunc([...old_value, ...args]));
        }));

        return {
            [property_names.current]: asyncCurrentAtom,
            [property_names.update]: updateAtom,
            [property_names.async_update]: asyncUpdateAtom,
            [property_names.add]: addAtom,
            [property_names.async_add]: asyncAddAtom,
        };
    };

    return { atomInstance, useHook };
};

export const { atomInstance: Atom_SoftwareVersion, useHook: useStore_SoftwareVersion } = createAtomWithHook("-", "SoftwareVersion");

export const { atomInstance: Atom_TranslationStatus, useHook: useStore_TranslationStatus } = createAsyncAtomWithHook(false, "TranslationStatus");
export const { atomInstance: Atom_TranscriptionSendStatus, useHook: useStore_TranscriptionSendStatus } = createAsyncAtomWithHook(false, "TranscriptionSendStatus");
export const { atomInstance: Atom_TranscriptionReceiveStatus, useHook: useStore_TranscriptionReceiveStatus } = createAsyncAtomWithHook(false, "TranscriptionReceiveStatus");
export const { atomInstance: Atom_ForegroundStatus, useHook: useStore_ForegroundStatus } = createAsyncAtomWithHook(false, "ForegroundStatus");

export const { atomInstance: Atom_MessageLogs, useHook: useStore_MessageLogs } = createAtomWithHook(generateTestData(20), "MessageLogs");
export const { atomInstance: Atom_IsMainPageCompactMode, useHook: useStore_IsMainPageCompactMode } = createAtomWithHook(false, "IsMainPageCompactMode");
export const { atomInstance: Atom_IsOpenedLanguageSelector, useHook: useStore_IsOpenedLanguageSelector } = createAtomWithHook(
    { your_language: false, target_language: false },
    "IsOpenedLanguageSelector"
);

export const { atomInstance: Atom_SelectableLanguageList, useHook: useStore_SelectableLanguageList } = createAtomWithHook([], "SelectableLanguageList");

export const { atomInstance: Atom_SelectedPresetTabNumber, useHook: useStore_SelectedPresetTabNumber } = createAtomWithHook(1, "SelectedPresetTabNumber");
export const { atomInstance: Atom_IsOpenedConfigPage, useHook: useStore_IsOpenedConfigPage } = createAtomWithHook(false, "IsOpenedConfigPage");
export const { atomInstance: Atom_SelectedConfigTabId, useHook: useStore_SelectedConfigTabId } = createAtomWithHook("device", "SelectedConfigTabId");
export const { atomInstance: Atom_IsOpenedDropdownMenu, useHook: useStore_IsOpenedDropdownMenu } = createAtomWithHook("", "IsOpenedDropdownMenu");


// Config Page
export const { atomInstance: Atom_MicHostList, useHook: useStore_MicHostList } = createAsyncAtomWithHook({}, "MicHostList");
export const { atomInstance: Atom_SelectedMicHost, useHook: useStore_SelectedMicHost } = createAsyncAtomWithHook("Nothing Selected", "SelectedMicHost");
export const { atomInstance: Atom_MicDeviceList, useHook: useStore_MicDeviceList } = createAsyncAtomWithHook({}, "MicDeviceList");
export const { atomInstance: Atom_SelectedMicDevice, useHook: useStore_SelectedMicDevice } = createAsyncAtomWithHook("Nothing Selected", "SelectedMicDevice");

export const { atomInstance: Atom_SpeakerDeviceList, useHook: useStore_SpeakerDeviceList } = createAsyncAtomWithHook({}, "SpeakerDeviceList");
export const { atomInstance: Atom_SelectedSpeakerDevice, useHook: useStore_SelectedSpeakerDevice } = createAsyncAtomWithHook("Nothing Selected", "SelectedSpeakerDevice");

export const { atomInstance: Atom_MicVolume, useHook: useStore_MicVolume } = createAsyncAtomWithHook(0, "MicVolume");
export const { atomInstance: Atom_SpeakerVolume, useHook: useStore_SpeakerVolume } = createAsyncAtomWithHook(0, "SpeakerVolume");

export const { atomInstance: Atom_MicThresholdCheckStatus, useHook: useStore_MicThresholdCheckStatus } = createAsyncAtomWithHook(false, "MicThresholdCheckStatus");
export const { atomInstance: Atom_SpeakerThresholdCheckStatus, useHook: useStore_SpeakerThresholdCheckStatus } = createAsyncAtomWithHook(false, "SpeakerThresholdCheckStatus");

export const { atomInstance: Atom_MicThreshold, useHook: useStore_MicThreshold } = createAtomWithHook(0, "MicThreshold");
export const { atomInstance: Atom_SpeakerThreshold, useHook: useStore_SpeakerThreshold } = createAtomWithHook(0, "SpeakerThreshold");

export const { atomInstance: Atom_EnableAutomaticMicThreshold, useHook: useStore_EnableAutomaticMicThreshold } = createAsyncAtomWithHook(false, "EnableAutomaticMicThreshold");
export const { atomInstance: Atom_EnableAutomaticSpeakerThreshold, useHook: useStore_EnableAutomaticSpeakerThreshold } = createAsyncAtomWithHook(false, "EnableAutomaticSpeakerThreshold");


// Appearance
export const { atomInstance: Atom_UiLanguage, useHook: useStore_UiLanguage } = createAsyncAtomWithHook("en", "UiLanguage");








export const { atomInstance: Atom_SendMessageFormat, useHook: useStore_SendMessageFormat } = createAtomWithHook({
    before: "",
    after: "",
}, "SendMessageFormat");
export const { atomInstance: Atom_SendMessageFormatWithT, useHook: useStore_SendMessageFormatWithT } = createAtomWithHook({
    before: "",
    between: "",
    after: "",
    is_message_first: true,
}, "SendMessageFormatWithT");
export const { atomInstance: Atom_ReceivedMessageFormat, useHook: useStore_ReceivedMessageFormat } = createAtomWithHook({
    before: "",
    after: "",
}, "ReceivedMessageFormat");
export const { atomInstance: Atom_ReceivedMessageFormatWithT, useHook: useStore_ReceivedMessageFormatWithT } = createAtomWithHook({
    before: "",
    between: "",
    after: "",
    is_message_first: true,
}, "ReceivedMessageFormatWithT");

export const { atomInstance: Atom_IsOpenedWordFilterList, useHook: useStore_IsOpenedWordFilterList } = createAtomWithHook(false, "IsOpenedWordFilterList");
export const { atomInstance: Atom_WordFilterList, useHook: useStore_WordFilterList } = createAtomWithHook(word_filter_list, "WordFilterList");


// Others
export const { atomInstance: Atom_EnableAutoClearMessageBox, useHook: useStore_EnableAutoClearMessageBox } = createAsyncAtomWithHook(true, "EnableAutoClearMessageBox");
export const { atomInstance: Atom_SendMessageButtonType, useHook: useStore_SendMessageButtonType } = createAsyncAtomWithHook("show", "SendMessageButtonType");


export const { atomInstance: Atom_TranslatorList, useHook: useStore_TranslatorList } = createAtomWithHook(translator_list, "TranslatorList");
export const { atomInstance: Atom_SelectedTranslatorId, useHook: useStore_SelectedTranslatorId } = createAtomWithHook("CTranslate2", "SelectedTranslatorId");
export const { atomInstance: Atom_IsOpenedTranslatorSelector, useHook: useStore_IsOpenedTranslatorSelector } = createAtomWithHook(false, "IsOpenedTranslatorSelector");

export const { atomInstance: Atom_VrctPosterIndex, useHook: useStore_VrctPosterIndex } = createAtomWithHook(0, "VrctPosterIndex");
export const { atomInstance: Atom_PosterShowcaseWorldPageIndex, useHook: useStore_PosterShowcaseWorldPageIndex } = createAtomWithHook(0, "PosterShowcaseWorldPageIndex");