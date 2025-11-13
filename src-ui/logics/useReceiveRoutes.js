import * as common from "@logics_common";
import * as main from "@logics_main";
import * as configs from "@logics_configs";
import { _useBackendErrorHandling } from "./_useBackendErrorHandling";
import { SETTINGS_ARRAY } from "./configs/config_page_setter/ui_config_setter";

export const STATIC_ROUTE_META_LIST = [
    // Common
    { endpoint: "/run/feed_watchdog", ns: null, hook_name: null, method_name: null },
    { endpoint: "/run/initialization_progress", ns: common, hook_name: "useInitProgress", method_name: "updateInitProgress" },
    { endpoint: "/run/enable_ai_models", ns: common, hook_name: "useIsVrctAvailable", method_name: "handleAiModelsAvailability" },
    { endpoint: "/get/data/compute_mode", ns: common, hook_name: "useComputeMode", method_name: "updateComputeMode" },

    { endpoint: "/run/update_software", ns: null, hook_name: null, method_name: null },
    { endpoint: "/run/update_cuda_software", ns: null, hook_name: null, method_name: null },

    { endpoint: "/get/data/main_window_geometry", ns: common, hook_name: "useWindow", method_name: "restoreWindowGeometry" },
    { endpoint: "/set/data/main_window_geometry", ns: null, hook_name: null, method_name: null },

    { endpoint: "/run/open_filepath_logs", ns: common, hook_name: "useOpenFolder", method_name: "openedFolder_MessageLogs" },
    { endpoint: "/run/open_filepath_config_file", ns: common, hook_name: "useOpenFolder", method_name: "openedFolder_ConfigFile" },

    // Software Version
    { endpoint: "/get/data/version", ns: common, hook_name: "useSoftwareVersion", method_name: "updateSoftwareVersion" },
    // Latest Software Version Info
    { endpoint: "/run/software_update_info", ns: common, hook_name: "useSoftwareVersion", method_name: "updateSoftwareVersionInfo" },

    { endpoint: "/run/connected_network", ns: common, hook_name: "useHandleNetworkConnection", method_name: "handleNetworkConnection" },
    { endpoint: "/run/enable_osc_query", ns: common, hook_name: "useHandleOscQuery", method_name: "handleOscQuery" },

    // Message (By typing)
    { endpoint: "/run/send_message_box", ns: common, hook_name: "useMessage", method_name: "updateSentMessageLogById" },
    { endpoint: "/run/typing_message_box", ns: null, hook_name: null, method_name: null },
    { endpoint: "/run/stop_typing_message_box", ns: null, hook_name: null, method_name: null },
    // Message Transcription
    { endpoint: "/run/transcription_send_mic_message", ns: common, hook_name: "useMessage", method_name: "addSentMessageLog" },
    { endpoint: "/run/transcription_receive_speaker_message", ns: common, hook_name: "useMessage", method_name: "addReceivedMessageLog" },

    // System Messages
    { endpoint: "/run/word_filter", ns: common, hook_name: "useMessage", method_name: "addSystemMessageLog_FromBackend" },


    // Volume
    { endpoint: "/run/check_mic_volume", ns: common, hook_name: "useVolume", method_name: "updateVolumeVariable_Mic" },
    { endpoint: "/run/check_speaker_volume", ns: common, hook_name: "useVolume", method_name: "updateVolumeVariable_Speaker" },
    { endpoint: "/set/enable/check_mic_threshold", ns: common, hook_name: "useVolume", method_name: "updateMicThresholdCheckStatus" },
    { endpoint: "/set/disable/check_mic_threshold", ns: common, hook_name: "useVolume", method_name: "updateMicThresholdCheckStatus" },
    { endpoint: "/set/enable/check_speaker_threshold", ns: common, hook_name: "useVolume", method_name: "updateSpeakerThresholdCheckStatus" },
    { endpoint: "/set/disable/check_speaker_threshold", ns: common, hook_name: "useVolume", method_name: "updateSpeakerThresholdCheckStatus" },




    // Main Page
    // Page Controls
    { endpoint: "/get/data/main_window_sidebar_compact_mode", ns: main, hook_name: "useIsMainPageCompactMode", method_name: "updateIsMainPageCompactMode" },
    { endpoint: "/set/enable/main_window_sidebar_compact_mode", ns: main, hook_name: "useIsMainPageCompactMode", method_name: "updateIsMainPageCompactMode" },
    { endpoint: "/set/disable/main_window_sidebar_compact_mode", ns: main, hook_name: "useIsMainPageCompactMode", method_name: "updateIsMainPageCompactMode" },

    // Main Functions
    { endpoint: "/set/enable/translation", ns: main, hook_name: "useMainFunction", method_name: "updateTranslationStatus" },
    { endpoint: "/set/disable/translation", ns: main, hook_name: "useMainFunction", method_name: "updateTranslationStatus" },
    { endpoint: "/set/enable/transcription_send", ns: main, hook_name: "useMainFunction", method_name: "updateTranscriptionSendStatus" },
    { endpoint: "/set/disable/transcription_send", ns: main, hook_name: "useMainFunction", method_name: "updateTranscriptionSendStatus" },
    { endpoint: "/set/enable/transcription_receive", ns: main, hook_name: "useMainFunction", method_name: "updateTranscriptionReceiveStatus" },
    { endpoint: "/set/disable/transcription_receive", ns: main, hook_name: "useMainFunction", method_name: "updateTranscriptionReceiveStatus" },

    // Language Settings
    { endpoint: "/get/data/selected_tab_no", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedPresetTabNumber" },
    { endpoint: "/set/data/selected_tab_no", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedPresetTabNumber" },

    { endpoint: "/get/data/selected_your_languages", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedYourLanguages" },
    { endpoint: "/set/data/selected_your_languages", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedYourLanguages" },
    { endpoint: "/get/data/selected_target_languages", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedTargetLanguages" },
    { endpoint: "/set/data/selected_target_languages", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedTargetLanguages" },

    { endpoint: "/get/data/selectable_translation_engines", ns: main, hook_name: "useLanguageSettings", method_name: "updateTranslatorAvailability" },
    { endpoint: "/run/translation_engines", ns: main, hook_name: "useLanguageSettings", method_name: "updateTranslatorAvailability" },

    { endpoint: "/get/data/selected_translation_engines", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedTranslationEngines" },
    { endpoint: "/set/data/selected_translation_engines", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedTranslationEngines" },
    { endpoint: "/run/selected_translation_engines", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedTranslationEngines" },

    { endpoint: "/run/swap_your_language_and_target_language", ns: main, hook_name: "useLanguageSettings", method_name: "updateBothSelectedLanguages" },

    // Language Selector
    { endpoint: "/get/data/selectable_language_list", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectableLanguageList" },


    // Message Input Box
    { endpoint: "/get/data/message_box_ratio", ns: main, hook_name: "useMessageInputBoxRatio", method_name: "updateMessageInputBoxRatio" },
    { endpoint: "/set/data/message_box_ratio", ns: main, hook_name: "useMessageInputBoxRatio", method_name: "updateMessageInputBoxRatio" },


    // // Config Page
    // Hotkeys
    { endpoint: "/get/data/hotkeys", ns: configs, hook_name: "useHotkeys", method_name: "updateHotkeys" },
    { endpoint: "/set/data/hotkeys", ns: configs, hook_name: "useHotkeys", method_name: "setSuccessHotkeys" },

    // Plugins
    { endpoint: "/get/data/plugins_status", ns: configs, hook_name: "usePlugins", method_name: "updateSavedPluginsStatus" },
    { endpoint: "/set/data/plugins_status", ns: configs, hook_name: "usePlugins", method_name: "setSuccessSavedPluginsStatus" },

    // // Not Implemented Yet...
    { endpoint: "/get/data/selectable_transcription_engines", ns: null, hook_name: null, method_name: null }, // Not implemented on UI yet. (if ai_models has not been detected, this will be blank array[]. if the ai_models are ok but just network has not connected, it'l be only ["Whisper"])
];

export const useReceiveRoutes = () => {
    const { showNotification_Error } = common.useNotificationStatus();
    const { errorHandling_Backend } = _useBackendErrorHandling();
    const { updateIsBackendReady } = common.useIsBackendReady();

    const ROUTE_META_LIST = buildRouteMetaList();

    const handleInvalidEndpoint = (parsed_data) => {
        console.error(`Invalid endpoint: ${parsed_data.endpoint}\nresult: ${JSON.stringify(parsed_data.result)}`);
    };

    const hook_results = {};
    ROUTE_META_LIST.forEach(({ ns, hook_name }) => {
        if (ns && hook_name && !(hook_name in hook_results)) {
            const hookFn = ns[hook_name];
            if (typeof hookFn === "function") {
                hook_results[hook_name] = hookFn();
            } else {
                console.warn(`Hook not found on namespace: ${hook_name}`);
                hook_results[hook_name] = {};
            }
        }
    });

    const noop = () => {};

    const routes = Object.fromEntries(
        ROUTE_META_LIST.map(({ endpoint, hook_name, method_name }) => {
            const result_obj = hook_results[hook_name] || {};
            const fn = result_obj[method_name];
            if (fn === undefined && method_name !== null) {
                console.error("Method not found.", { endpoint, hook_name, method_name, result_obj, fn });
            }
            return [endpoint, typeof fn === "function" ? fn : noop];
        })
    );


    const receiveRoutes = (parsed_data) => {
        const { endpoint, status, result } = parsed_data;

        if (endpoint === "/run/initialization_complete") {
            Object.entries(result).forEach(([ep, value]) => {
                if (ep in routes) {
                    routes[ep](value);
                } else {
                    handleInvalidEndpoint({ endpoint: ep, result: value });
                }
            });
            updateIsBackendReady(true);
            return;
        }

        switch (status) {
            case 200:
                if (endpoint in routes) {
                    routes[endpoint](result);
                } else {
                    handleInvalidEndpoint(parsed_data);
                }
                break;

            case 400:
                errorHandling_Backend({
                    message: parsed_data.result.message,
                    data: parsed_data.result.data,
                    endpoint: parsed_data.endpoint,
                    result: parsed_data.result,
                });
                break;

            case 348:
                // console.log(`from backend: %c ${JSON.stringify(parsed_data)}`, style_348);
                break;

            case 500:
                showNotification_Error(
                    `An error occurred. Please restart VRCT or contact the developers. ${JSON.stringify(parsed_data.result)}`, { hide_duration: null });
                break;

            default:
                console.log("Received data status does not match.", parsed_data);
        }
    };

    return { receiveRoutes };
};

const style_348 = [
    "color: gray",
].join(";");



// Automatically set 'configs' for now.(This is only used in config)
const buildRouteMetaList = () => {
    const namespace_module = configs;
    const generated = [];

    for (const s of SETTINGS_ARRAY) {
        const category = s.Category;
        const base = s.Base_Name;
        const ep = s.base_endpoint_name;
        const hookName = `use${category}`;
        const setSuccessMethodName = `setSuccess${base}`;
        const deleteSuccessMethodName = `deleteSuccess${base}`;
        const updateFromBackendMethodName = `updateFromBackend${base}`;


        if (s.add_endpoint_run_array?.includes("from_backend")) {
            generated.push({
                endpoint: `/run/${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: updateFromBackendMethodName,
            });
        }



        generated.push({
            endpoint: `/get/data/${ep}`,
            ns: namespace_module,
            hook_name: hookName,
            method_name: updateFromBackendMethodName,
        });

        if (s.logics_template_id === "get_set_delete") {
            generated.push({
                endpoint: `/delete/data/${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: deleteSuccessMethodName,
            });
        }

        if (s.logics_template_id !== "get_list") {
            generated.push({
                endpoint: `/set/data/${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: setSuccessMethodName,
            });
        }

        if (s.logics_template_id === "toggle_enable_disable" || s.ui_template_id === "toggle") {
            generated.push({
                endpoint: `/set/enable/${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: setSuccessMethodName,
            });
            generated.push({
                endpoint: `/set/disable/${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: setSuccessMethodName,
            });
        }

        if (s.logics_template_id === "weight_download_status") {
            generated.push({
                endpoint: `/get/data/selectable_${ep}_type_dict`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: `updateDownloaded${base}`,
            });

            generated.push({
                endpoint: `/set/data/${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: setSuccessMethodName,
            });

            generated.push({
                endpoint: `/run/download_progress_${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: `updateDownloadProgress${base}`,
            });

            generated.push({
                endpoint: `/run/downloaded_${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: `downloaded${base}`,
            });
            generated.push({
                endpoint: `/run/pending_${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: `pending${base}`,
            });
            generated.push({
                endpoint: `/run/download_${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: `downloaded${base}`,
            });
            generated.push({
                endpoint: `/get/data/${ep}`,
                ns: namespace_module,
                hook_name: hookName,
                method_name: updateFromBackendMethodName,
            });
            continue;
        }
    }

    const mergedMap = new Map();

    for (const item of STATIC_ROUTE_META_LIST) {
        if (!item || !item.endpoint) continue;
        mergedMap.set(item.endpoint, {
            endpoint: item.endpoint,
            ns: item.ns ?? null,
            hook_name: item.hook_name ?? null,
            method_name: item.method_name ?? null,
        });
    }

    for (const gen of generated) {
        const ep = gen.endpoint;
        const existing = mergedMap.get(ep);
        if (!existing) {
            mergedMap.set(ep, { ...gen });
            continue;
        }

        const merged = {
            endpoint: ep,
            ns: existing.ns ?? gen.ns ?? null,
            hook_name: existing.hook_name ?? gen.hook_name ?? null,
            method_name: existing.method_name ?? gen.method_name ?? null,
        };
        mergedMap.set(ep, merged);
    }

    const mergedList = [];


    for (const item of STATIC_ROUTE_META_LIST) {
        if (!item || !item.endpoint) continue;
        const merged = mergedMap.get(item.endpoint);
        if (merged) {
            mergedList.push(merged);
            mergedMap.delete(item.endpoint);
        }
    }

    for (const gen of generated) {
        const ep = gen.endpoint;
        if (mergedMap.has(ep)) {
            mergedList.push(mergedMap.get(ep));
            mergedMap.delete(ep);
        }
    }

    for (const remaining of mergedMap.values()) {
        mergedList.push(remaining);
    }

    return mergedList;
};