import {
    atom,
    useAtomValue,
    useSetAtom
} from "jotai";

import {
    generateTestConversationData,
} from "./_test_data.js"

import {
    translator_status,
} from "@ui_configs";

export const store = {
    backend_subprocess: null,
    setting_box_scroll_container: null,
    log_box_ref: null,
    text_area_ref: null,
    is_initialized_load_plugin: false,
    is_fetched_plugins_info_already: false,
    is_initialized_fetched_plugin_info: false,
    last_executed_time_startTyping: 0,
};

const generatePropertyNames = (base_name) => ({
    error: `error${base_name}`,
    pending: `pending${base_name}`,
    current: `current${base_name}`,
    update: `update${base_name}`,
    add: `add${base_name}`,
});

export const dynamicStoreRegistry = {};

export const createAtomWithHook = (initialValue, base_name, options) => {
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

        const updateAtom = (payload, options = {}) => {
            const { remain_state = false, set_state, lock_state } = options;

            setAtom((currentValue) => {
                let new_state;
                if (lock_state) {
                    new_state = set_state;
                } else {
                    if (currentValue.lock_state) {
                        new_state = currentValue.state;
                    } else {
                        new_state = set_state ?? (remain_state ? currentValue.state : "ok");
                    }
                }

                const updated_data = typeof payload === "function"
                    ? payload(currentValue)
                    : payload;

                return {
                    state: new_state,
                    data: updated_data,
                };
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

    try {
        const hookName = `useStore_${base_name}`;
        const atomName = `Atom_${base_name}`;
        dynamicStoreRegistry[hookName] = useHook;
        dynamicStoreRegistry[atomName] = atomInstance;
    } catch (e) {
        console.warn("dynamic registration failed for", base_name, e);
    }

    return { atomInstance, useHook };
};


export const getStoreHook = (baseName) => {
    const hookName = `useStore_${baseName}`;
    return dynamicStoreRegistry[hookName];
};

export const registerMany = (settingsArray = []) => {
    for (const s of settingsArray) {
        try {
            const hookName = `useStore_${s.Base_Name}`;
            if (dynamicStoreRegistry[hookName]) {
                continue;
            }

            createAtomWithHook(s.default_value, s.Base_Name, s.options || {});
        } catch (e) {
            console.warn("registerMany failed for", s.Base_Name, e);
        }
    }
};



// Common
export const { atomInstance: Atom_IsBackendReady, useHook: useStore_IsBackendReady } = createAtomWithHook(false, "IsBackendReady");
export const { atomInstance: Atom_IsVrctAvailable, useHook: useStore_IsVrctAvailable } = createAtomWithHook(true, "IsVrctAvailable");
export const { atomInstance: Atom_IsOscAvailable, useHook: useStore_IsOscAvailable } = createAtomWithHook(true, "IsOscAvailable");
export const { atomInstance: Atom_ComputeMode, useHook: useStore_ComputeMode } = createAtomWithHook("", "ComputeMode");
export const { atomInstance: Atom_IsOpenedConfigPage, useHook: useStore_IsOpenedConfigPage } = createAtomWithHook(false, "IsOpenedConfigPage");
export const { atomInstance: Atom_MainFunctionsStateMemory, useHook: useStore_MainFunctionsStateMemory } = createAtomWithHook({
    transcription_send: false,
    transcription_receive: false,
}, "MainFunctionsStateMemory");
export const { atomInstance: Atom_OpenedQuickSetting, useHook: useStore_OpenedQuickSetting } = createAtomWithHook("", "OpenedQuickSetting");
export const { atomInstance: Atom_LatestSoftwareVersionInfo, useHook: useStore_LatestSoftwareVersionInfo } = createAtomWithHook({
    is_update_available: false,
    new_version: "0.0.0",
}, "LatestSoftwareVersionInfo");
export const { atomInstance: Atom_InitProgress, useHook: useStore_InitProgress } = createAtomWithHook(0, "InitProgress");
export const { atomInstance: Atom_IsBreakPoint, useHook: useStore_IsBreakPoint } = createAtomWithHook(false, "IsBreakPoint");
export const { atomInstance: Atom_IsSoftwareUpdating, useHook: useStore_IsSoftwareUpdating } = createAtomWithHook(false, "IsSoftwareUpdating");
export const { atomInstance: Atom_NotificationStatus, useHook: useStore_NotificationStatus } = createAtomWithHook({
    status: "",
    is_open: false,
    key: 0,
    message: "",
}, "NotificationStatus");
export const { atomInstance: Atom_IsLMStudioConnected, useHook: useStore_IsLMStudioConnected } = createAtomWithHook(false, "IsLMStudioConnected", {is_state_ok: true});
export const { atomInstance: Atom_IsOllamaConnected, useHook: useStore_IsOllamaConnected } = createAtomWithHook(false, "IsOllamaConnected", {is_state_ok: true});

// Main Page
// Common
export const { atomInstance: Atom_IsMainPageCompactMode, useHook: useStore_IsMainPageCompactMode } = createAtomWithHook(false, "IsMainPageCompactMode");

// Sidebar Section
export const { atomInstance: Atom_TranslationStatus, useHook: useStore_TranslationStatus } = createAtomWithHook(false, "TranslationStatus", {is_state_ok: true});
export const { atomInstance: Atom_TranscriptionSendStatus, useHook: useStore_TranscriptionSendStatus } = createAtomWithHook(false, "TranscriptionSendStatus", {is_state_ok: true});
export const { atomInstance: Atom_TranscriptionReceiveStatus, useHook: useStore_TranscriptionReceiveStatus } = createAtomWithHook(false, "TranscriptionReceiveStatus", {is_state_ok: true});
export const { atomInstance: Atom_ForegroundStatus, useHook: useStore_ForegroundStatus } = createAtomWithHook(false, "ForegroundStatus", {is_state_ok: true});

export const { atomInstance: Atom_SelectedPresetTabNumber, useHook: useStore_SelectedPresetTabNumber } = createAtomWithHook("1", "SelectedPresetTabNumber");
export const { atomInstance: Atom_SelectedYourLanguages, useHook: useStore_SelectedYourLanguages } = createAtomWithHook({}, "SelectedYourLanguages");
export const { atomInstance: Atom_SelectedTargetLanguages, useHook: useStore_SelectedTargetLanguages } = createAtomWithHook({}, "SelectedTargetLanguages");

export const { atomInstance: Atom_TranslationEngines, useHook: useStore_TranslationEngines } = createAtomWithHook(translator_status, "TranslationEngines");
export const { atomInstance: Atom_SelectedTranslationEngines, useHook: useStore_SelectedTranslationEngines } = createAtomWithHook({1:"", 2:"", 3:""}, "SelectedTranslationEngines");
export const { atomInstance: Atom_IsOpenedTranslatorSelector, useHook: useStore_IsOpenedTranslatorSelector } = createAtomWithHook(false, "IsOpenedTranslatorSelector");

// Language Selector
export const { atomInstance: Atom_IsOpenedLanguageSelector, useHook: useStore_IsOpenedLanguageSelector } = createAtomWithHook(
    { your_language: false, target_language: false, target_key: "1" },
    "IsOpenedLanguageSelector"
);
export const { atomInstance: Atom_SelectableLanguageList, useHook: useStore_SelectableLanguageList } = createAtomWithHook([], "SelectableLanguageList");

// Message Container
export const { atomInstance: Atom_MessageLogs, useHook: useStore_MessageLogs } = createAtomWithHook([], "MessageLogs");
// export const { atomInstance: Atom_MessageLogs, useHook: useStore_MessageLogs } = createAtomWithHook(generateTestConversationData(20), "MessageLogs"); // For testing
export const { atomInstance: Atom_MessageInputBoxRatio, useHook: useStore_MessageInputBoxRatio } = createAtomWithHook(20, "MessageInputBoxRatio");
export const { atomInstance: Atom_MessageInputValue, useHook: useStore_MessageInputValue } = createAtomWithHook("", "MessageInputValue");



// Config Page
// Common
export const { atomInstance: Atom_SoftwareVersion, useHook: useStore_SoftwareVersion } = createAtomWithHook("-", "SoftwareVersion");
export const { atomInstance: Atom_SelectedConfigTabId, useHook: useStore_SelectedConfigTabId } = createAtomWithHook("device", "SelectedConfigTabId");
export const { atomInstance: Atom_SettingBoxScrollPosition, useHook: useStore_SettingBoxScrollPosition } = createAtomWithHook(0, "SettingBoxScrollPosition");
export const { atomInstance: Atom_IsOpenedDropdownMenu, useHook: useStore_IsOpenedDropdownMenu } = createAtomWithHook("", "IsOpenedDropdownMenu");

// Device
export const { atomInstance: Atom_MicVolume, useHook: useStore_MicVolume } = createAtomWithHook(0, "MicVolume");
export const { atomInstance: Atom_SpeakerVolume, useHook: useStore_SpeakerVolume } = createAtomWithHook(0, "SpeakerVolume");

export const { atomInstance: Atom_MicThresholdCheckStatus, useHook: useStore_MicThresholdCheckStatus } = createAtomWithHook(false, "MicThresholdCheckStatus", {is_state_ok: true});
export const { atomInstance: Atom_SpeakerThresholdCheckStatus, useHook: useStore_SpeakerThresholdCheckStatus } = createAtomWithHook(false, "SpeakerThresholdCheckStatus", {is_state_ok: true});

export const { atomInstance: Atom_SelectableFontFamilyList, useHook: useStore_SelectableFontFamilyList } = createAtomWithHook({}, "SelectableFontFamilyList");


export const { atomInstance: Atom_IsOpenedMicWordFilterList, useHook: useStore_IsOpenedMicWordFilterList } = createAtomWithHook(false, "IsOpenedMicWordFilterList");

export const { atomInstance: Atom_MessageFormat_ExampleViewFilter, useHook: useStore_MessageFormat_ExampleViewFilter } = createAtomWithHook({
    send: "Simplified",
    received: "Simplified",
}, "MessageFormat_ExampleViewFilter");


// Hotkeys
export const { atomInstance: Atom_Hotkeys, useHook: useStore_Hotkeys } = createAtomWithHook({
    toggle_vrct_visibility: null,
    toggle_translation: null,
    toggle_transcription_send: null,
    toggle_transcription_receive: null,
}, "Hotkeys");

// Plugins
export const { atomInstance: Atom_FetchedPluginsInfo, useHook: useStore_FetchedPluginsInfo } = createAtomWithHook([], "FetchedPluginsInfo");
export const { atomInstance: Atom_LoadedPlugins, useHook: useStore_LoadedPlugins } = createAtomWithHook([], "LoadedPlugins");
export const { atomInstance: Atom_SavedPluginsStatus, useHook: useStore_SavedPluginsStatus } = createAtomWithHook([], "SavedPluginsStatus");
export const { atomInstance: Atom_PluginsData, useHook: useStore_PluginsData } = createAtomWithHook([], "PluginsData");

// Supporters
export const { atomInstance: Atom_SupportersData, useHook: useStore_SupportersData } = createAtomWithHook(null, "SupportersData", {is_state_ok: true});

// About VRCT
export const { atomInstance: Atom_VrctPosterIndex, useHook: useStore_VrctPosterIndex } = createAtomWithHook(0, "VrctPosterIndex");
export const { atomInstance: Atom_PosterShowcaseWorldPageIndex, useHook: useStore_PosterShowcaseWorldPageIndex } = createAtomWithHook(0, "PosterShowcaseWorldPageIndex");