import {
    atom,
    useAtomValue,
    useSetAtom
} from "jotai";

import {
    translator_status,
    generateTestData,
    word_filter_list,
} from "@data";

export const store = {
    backend_subprocess: null,
    config_page: null,
    log_box_ref: null,
};

const generatePropertyNames = (base_ame) => ({
    error: `error${base_ame}`,
    pending: `pending${base_ame}`,
    current: `current${base_ame}`,
    update: `update${base_ame}`,
    updatePart: `updatePart${base_ame}`,
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


const createAtomWithHook_WIP = (initialValue, base_ame, options) => {
    const property_names = generatePropertyNames(base_ame);
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



export const { atomInstance: Atom_SoftwareVersion, useHook: useStore_SoftwareVersion } = createAtomWithHook_WIP("-", "SoftwareVersion");

export const { atomInstance: Atom_TranslationStatus, useHook: useStore_TranslationStatus } = createAtomWithHook_WIP(false, "TranslationStatus", {is_state_ok: true});
export const { atomInstance: Atom_TranscriptionSendStatus, useHook: useStore_TranscriptionSendStatus } = createAtomWithHook_WIP(false, "TranscriptionSendStatus", {is_state_ok: true});
export const { atomInstance: Atom_TranscriptionReceiveStatus, useHook: useStore_TranscriptionReceiveStatus } = createAtomWithHook_WIP(false, "TranscriptionReceiveStatus", {is_state_ok: true});
export const { atomInstance: Atom_ForegroundStatus, useHook: useStore_ForegroundStatus } = createAtomWithHook_WIP(false, "ForegroundStatus", {is_state_ok: true});

export const { atomInstance: Atom_MessageLogs, useHook: useStore_MessageLogs } = createAtomWithHook_WIP(generateTestData(20), "MessageLogs");
export const { atomInstance: Atom_IsMainPageCompactMode, useHook: useStore_IsMainPageCompactMode } = createAtomWithHook_WIP(false, "IsMainPageCompactMode");

export const { atomInstance: Atom_IsOpenedLanguageSelector, useHook: useStore_IsOpenedLanguageSelector } = createAtomWithHook_WIP(
    { your_language: false, target_language: false },
    "IsOpenedLanguageSelector"
);
export const { atomInstance: Atom_SelectableLanguageList, useHook: useStore_SelectableLanguageList } = createAtomWithHook_WIP([], "SelectableLanguageList");

export const { atomInstance: Atom_SelectedPresetTabNumber, useHook: useStore_SelectedPresetTabNumber } = createAtomWithHook_WIP("", "SelectedPresetTabNumber");
export const { atomInstance: Atom_EnableMultiTranslation, useHook: useStore_EnableMultiTranslation } = createAtomWithHook_WIP(false, "EnableMultiTranslation");
export const { atomInstance: Atom_SelectedYourLanguages, useHook: useStore_SelectedYourLanguages } = createAtomWithHook_WIP({}, "SelectedYourLanguages");
export const { atomInstance: Atom_SelectedTargetLanguages, useHook: useStore_SelectedTargetLanguages } = createAtomWithHook_WIP({}, "SelectedTargetLanguages");


export const { atomInstance: Atom_TranslationEngines, useHook: useStore_TranslationEngines } = createAtomWithHook_WIP(translator_status, "TranslationEngines");
export const { atomInstance: Atom_SelectedTranslationEngines, useHook: useStore_SelectedTranslationEngines } = createAtomWithHook_WIP({}, "SelectedTranslationEngines");


export const { atomInstance: Atom_IsOpenedConfigPage, useHook: useStore_IsOpenedConfigPage } = createAtomWithHook_WIP(false, "IsOpenedConfigPage");
export const { atomInstance: Atom_SelectedConfigTabId, useHook: useStore_SelectedConfigTabId } = createAtomWithHook_WIP("device", "SelectedConfigTabId");
export const { atomInstance: Atom_IsOpenedDropdownMenu, useHook: useStore_IsOpenedDropdownMenu } = createAtomWithHook_WIP("", "IsOpenedDropdownMenu");


// Config Page
export const { atomInstance: Atom_EnableAutoMicSelect, useHook: useStore_EnableAutoMicSelect } = createAtomWithHook_WIP(true, "EnableAutoMicSelect");
export const { atomInstance: Atom_EnableAutoSpeakerSelect, useHook: useStore_EnableAutoSpeakerSelect } = createAtomWithHook_WIP(true, "EnableAutoSpeakerSelect");

export const { atomInstance: Atom_MicHostList, useHook: useStore_MicHostList } = createAtomWithHook_WIP({}, "MicHostList");
export const { atomInstance: Atom_SelectedMicHost, useHook: useStore_SelectedMicHost } = createAtomWithHook_WIP("Nothing Selected", "SelectedMicHost");
export const { atomInstance: Atom_MicDeviceList, useHook: useStore_MicDeviceList } = createAtomWithHook_WIP({}, "MicDeviceList");
export const { atomInstance: Atom_SelectedMicDevice, useHook: useStore_SelectedMicDevice } = createAtomWithHook_WIP("Nothing Selected", "SelectedMicDevice");

export const { atomInstance: Atom_SpeakerDeviceList, useHook: useStore_SpeakerDeviceList } = createAtomWithHook_WIP({}, "SpeakerDeviceList");
export const { atomInstance: Atom_SelectedSpeakerDevice, useHook: useStore_SelectedSpeakerDevice } = createAtomWithHook_WIP("Nothing Selected", "SelectedSpeakerDevice");

export const { atomInstance: Atom_MicVolume, useHook: useStore_MicVolume } = createAtomWithHook_WIP(0, "MicVolume");
export const { atomInstance: Atom_SpeakerVolume, useHook: useStore_SpeakerVolume } = createAtomWithHook_WIP(0, "SpeakerVolume");

export const { atomInstance: Atom_MicThresholdCheckStatus, useHook: useStore_MicThresholdCheckStatus } = createAtomWithHook_WIP(false, "MicThresholdCheckStatus", {is_state_ok: true});
export const { atomInstance: Atom_SpeakerThresholdCheckStatus, useHook: useStore_SpeakerThresholdCheckStatus } = createAtomWithHook_WIP(false, "SpeakerThresholdCheckStatus", {is_state_ok: true});

export const { atomInstance: Atom_MicThreshold, useHook: useStore_MicThreshold } = createAtomWithHook_WIP(0, "MicThreshold");
export const { atomInstance: Atom_SpeakerThreshold, useHook: useStore_SpeakerThreshold } = createAtomWithHook_WIP(0, "SpeakerThreshold");

export const { atomInstance: Atom_EnableAutomaticMicThreshold, useHook: useStore_EnableAutomaticMicThreshold } = createAtomWithHook_WIP(false, "EnableAutomaticMicThreshold");
export const { atomInstance: Atom_EnableAutomaticSpeakerThreshold, useHook: useStore_EnableAutomaticSpeakerThreshold } = createAtomWithHook_WIP(false, "EnableAutomaticSpeakerThreshold");


// Appearance
export const { atomInstance: Atom_UiLanguage, useHook: useStore_UiLanguage } = createAtomWithHook_WIP("en", "UiLanguage");








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

export const { atomInstance: Atom_IsOpenedWordFilterList, useHook: useStore_IsOpenedWordFilterList } = createAtomWithHook_WIP(false, "IsOpenedWordFilterList");
export const { atomInstance: Atom_WordFilterList, useHook: useStore_WordFilterList } = createAtomWithHook_WIP(word_filter_list, "WordFilterList");


// Others
export const { atomInstance: Atom_EnableAutoClearMessageBox, useHook: useStore_EnableAutoClearMessageBox } = createAtomWithHook_WIP(true, "EnableAutoClearMessageBox");
export const { atomInstance: Atom_SendMessageButtonType, useHook: useStore_SendMessageButtonType } = createAtomWithHook_WIP("show", "SendMessageButtonType");


export const { atomInstance: Atom_IsOpenedTranslatorSelector, useHook: useStore_IsOpenedTranslatorSelector } = createAtomWithHook_WIP(false, "IsOpenedTranslatorSelector");

export const { atomInstance: Atom_VrctPosterIndex, useHook: useStore_VrctPosterIndex } = createAtomWithHook_WIP(0, "VrctPosterIndex");
export const { atomInstance: Atom_PosterShowcaseWorldPageIndex, useHook: useStore_PosterShowcaseWorldPageIndex } = createAtomWithHook_WIP(0, "PosterShowcaseWorldPageIndex");