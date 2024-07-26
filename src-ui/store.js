import {
    atom,
    useAtomValue,
    useSetAtom
} from "jotai";

import { translator_list, generateTestData } from "@data";

export const store = {
    backend_subprocess: null,
    config_window: null,
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

export const { atomInstance: uiLanguage, useHook: useUiLanguage } = createAtomWithHook("en", "UiLanguage");
export const { atomInstance: State_Translation, useHook: useState_Translation } = createAsyncAtomWithHook(false, "State_Translation");
export const { atomInstance: State_TranscriptionSend, useHook: useState_TranscriptionSend } = createAsyncAtomWithHook(false, "State_TranscriptionSend");
export const { atomInstance: State_TranscriptionReceive, useHook: useState_TranscriptionReceive } = createAsyncAtomWithHook(false, "State_TranscriptionReceive");
export const { atomInstance: State_Foreground, useHook: useState_Foreground } = createAsyncAtomWithHook(false, "State_Foreground");

export const { atomInstance: messageLogs, useHook: useMessageLogs } = createAtomWithHook(generateTestData(20), "MessageLogs");
export const { atomInstance: isCompactMode, useHook: useIsCompactMode } = createAtomWithHook(false, "IsCompactMode");
export const { atomInstance: isOpenedLanguageSelector, useHook: useIsOpenedLanguageSelector } = createAtomWithHook(
    { your_language: false, target_language: false },
    "IsOpenedLanguageSelector"
);

export const { atomInstance: selectedTab, useHook: useSelectedTab } = createAtomWithHook(1, "SelectedTab");
export const { atomInstance: isOpenedConfigWindow, useHook: useIsOpenedConfigWindow } = createAtomWithHook(false, "IsOpenedConfigWindow");
export const { atomInstance: selectedConfigTab, useHook: useSelectedConfigTab } = createAtomWithHook("appearance", "SelectedConfigTab");
export const { atomInstance: openedDropdownMenu, useHook: useOpenedDropdownMenu } = createAtomWithHook("", "OpenedDropdownMenu");
export const { atomInstance: selectedMicDevice, useHook: useSelectedMicDevice } = createAsyncAtomWithHook("device b", "SelectedMicDevice");

const test_list = {
    a: "Device A",
    "device b": "Device B",
};

export const { atomInstance: micDeviceList, useHook: useMicDeviceList } = createAtomWithHook(test_list, "MicDeviceList");
export const { atomInstance: translatorList, useHook: useTranslatorList } = createAtomWithHook(translator_list, "TranslatorList");
export const { atomInstance: selectedTranslator, useHook: useSelectedTranslator } = createAtomWithHook("CTranslate2", "SelectedTranslator");
export const { atomInstance: openedTranslatorSelector, useHook: useOpenedTranslatorSelector } = createAtomWithHook(false, "OpenedTranslatorSelector");
export const { atomInstance: vrctPosterIndex, useHook: useVrctPosterIndex } = createAtomWithHook(0, "VrctPosterIndex");
export const { atomInstance: posterShowcaseWorldPageIndex, useHook: usePosterShowcaseWorldPageIndex } = createAtomWithHook(0, "PosterShowcaseWorldPageIndex");