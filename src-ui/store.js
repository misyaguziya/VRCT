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

const createAtomWithHook = (initialValue, property_names) => {
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
const createAsyncAtomWithHook = (initialValue, property_names) => {
    const atomInstance = atom(initialValue);
    const asyncAtom = atom(async (get) => get(atomInstance));

    const loadableAtom = loadable(asyncAtom);

    const useHook = () => {
        const asyncCurrentAtom = useAtomValue(loadableAtom);
        // const currentAtom = useAtomValue(atomInstance);

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
            const ald_value = await get(atomInstance);
            set(atomInstance, payloadAsyncFunc([...ald_value, ...args]));
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

export const { atomInstance: uiLanguage, useHook: useUiLanguage } = createAtomWithHook("en", {
    current: "currentUiLanguage",
    update: "updateUiLanguage",
});


export const { atomInstance: State_Translation, useHook: useState_Translation } = createAsyncAtomWithHook(false, {
    current: "currentState_Translation",
    update: "updateState_Translation",
    async_update: "asyncUpdateState_Translation",
});
export const { atomInstance: State_TranscriptionSend, useHook: useState_TranscriptionSend } = createAsyncAtomWithHook(false, {
    current: "currentState_TranscriptionSend",
    update: "updateState_TranscriptionSend",
    async_update: "asyncUpdateState_TranscriptionSend",
});
export const { atomInstance: State_TranscriptionReceive, useHook: useState_TranscriptionReceive } = createAsyncAtomWithHook(false, {
    current: "currentState_TranscriptionReceive",
    update: "updateState_TranscriptionReceive",
    async_update: "asyncUpdateState_TranscriptionReceive",
});
export const { atomInstance: State_Foreground, useHook: useState_Foreground } = createAsyncAtomWithHook(false, {
    current: "currentState_Foreground",
    update: "updateState_Foreground",
    async_update: "asyncUpdateState_Foreground",
});



export const { atomInstance: messageLogs, useHook: useMessageLogs } = createAtomWithHook(generateTestData(20), {
    current: "currentMessageLogs",
    update: "updateMessageLogs",
    add: "addMessageLogs",
});

export const { atomInstance: isCompactMode, useHook: useIsCompactMode } = createAtomWithHook(false, {
    current: "currentIsCompactMode",
    update: "updateIsCompactMode",
});

export const { atomInstance: isOpenedLanguageSelector, useHook: useIsOpenedLanguageSelector } = createAtomWithHook(
    { your_language: false, target_language: false },
    {
        current: "currentIsOpenedLanguageSelector",
        update: "updateIsOpenedLanguageSelector",
    }
);

export const { atomInstance: selectedTab, useHook: useSelectedTab } = createAtomWithHook(1, {
    current: "currentSelectedTab",
    update: "updateSelectedTab",
});


export const { atomInstance: isOpenedConfigWindow, useHook: useIsOpenedConfigWindow } = createAtomWithHook(false, {
    current: "currentIsOpenedConfigWindow",
    update: "updateIsOpenedConfigWindow",
} );

export const { atomInstance: selectedConfigTab, useHook: useSelectedConfigTab } = createAtomWithHook("appearance", {
    current: "currentSelectedConfigTab",
    update: "updateSelectedConfigTab",
});

export const { atomInstance: openedDropdownMenu, useHook: useOpenedDropdownMenu } = createAtomWithHook("", {
    current: "currentOpenedDropdownMenu",
    update: "updateOpenedDropdownMenu",
});


export const { atomInstance: selectedMicDevice, useHook: useSelectedMicDevice } = createAsyncAtomWithHook("device b", {
    current: "currentSelectedMicDevice",
    update: "updateSelectedMicDevice",
});
const test_list = {
    a: "Device A",
    "device b": "Device B",
};
export const { atomInstance: micDeviceList, useHook: useMicDeviceList } = createAtomWithHook(test_list, {
    current: "currentMicDeviceList",
    update: "updateMicDeviceList",
});

export const { atomInstance: translatorList, useHook: useTranslatorList } = createAtomWithHook(translator_list, {
    current: "currentTranslatorList",
    update: "updateTranslatorList",
});

export const { atomInstance: selectedTranslator, useHook: useSelectedTranslator } = createAtomWithHook("CTranslate2", {
    current: "currentSelectedTranslator",
    update: "updateSelectedTranslator",
});

export const { atomInstance: openedTranslatorSelector, useHook: useOpenedTranslatorSelector } = createAtomWithHook(false, {
    current: "currentOpenedTranslatorSelector",
    update: "updateOpenedTranslatorSelector",
});

export const { atomInstance: vrctPosterIndex, useHook: useVrctPosterIndex } = createAtomWithHook(0, {
    current: "currentVrctPosterIndex",
    update: "updateVrctPosterIndex",
});

export const { atomInstance: posterShowcaseWorldPageIndex, useHook: usePosterShowcaseWorldPageIndex } = createAtomWithHook(0, {
    current: "currentPosterShowcaseWorldPageIndex",
    update: "updatePosterShowcaseWorldPageIndex",
});