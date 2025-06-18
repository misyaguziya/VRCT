import {
    useStore_IsEnabledOverlaySmallLog,
    useStore_IsEnabledOverlayLargeLog,
    useStore_OverlaySmallLogSettings,
    useStore_OverlayLargeLogSettings,
    useStore_OverlayShowOnlyTranslatedMessages,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useVr = () => {
    const { asyncStdoutToPython } = useStdoutToPython();

    const { currentIsEnabledOverlaySmallLog, updateIsEnabledOverlaySmallLog, pendingIsEnabledOverlaySmallLog } = useStore_IsEnabledOverlaySmallLog();
    const { currentIsEnabledOverlayLargeLog, updateIsEnabledOverlayLargeLog, pendingIsEnabledOverlayLargeLog } = useStore_IsEnabledOverlayLargeLog();
    const { currentOverlaySmallLogSettings, updateOverlaySmallLogSettings, pendingOverlaySmallLogSettings } = useStore_OverlaySmallLogSettings();
    const { currentOverlayLargeLogSettings, updateOverlayLargeLogSettings, pendingOverlayLargeLogSettings } = useStore_OverlayLargeLogSettings();
    const { currentOverlayShowOnlyTranslatedMessages, updateOverlayShowOnlyTranslatedMessages, pendingOverlayShowOnlyTranslatedMessages } = useStore_OverlayShowOnlyTranslatedMessages();


    const getIsEnabledOverlaySmallLog = () => {
        pendingIsEnabledOverlaySmallLog();
        asyncStdoutToPython("/get/data/overlay_small_log");
    };

    const toggleIsEnabledOverlaySmallLog = () => {
        pendingIsEnabledOverlaySmallLog();
        if (currentIsEnabledOverlaySmallLog.data) {
            asyncStdoutToPython("/set/disable/overlay_small_log");
        } else {
            asyncStdoutToPython("/set/enable/overlay_small_log");
        }
    };


    const getIsEnabledOverlayLargeLog = () => {
        pendingIsEnabledOverlayLargeLog();
        asyncStdoutToPython("/get/data/overlay_large_log");
    };

    const toggleIsEnabledOverlayLargeLog = () => {
        pendingIsEnabledOverlayLargeLog();
        if (currentIsEnabledOverlayLargeLog.data) {
            asyncStdoutToPython("/set/disable/overlay_large_log");
        } else {
            asyncStdoutToPython("/set/enable/overlay_large_log");
        }
    };


    const getOverlaySmallLogSettings = () => {
        // pendingOverlaySmallLogSettings();
        asyncStdoutToPython("/get/data/overlay_small_log_settings");
    };

    const setOverlaySmallLogSettings = (overlay_small_log_settings) => {
        // pendingOverlaySmallLogSettings();
        asyncStdoutToPython("/set/data/overlay_small_log_settings", overlay_small_log_settings);
    };


    const getOverlayLargeLogSettings = () => {
        // pendingOverlayLargeLogSettings();
        asyncStdoutToPython("/get/data/overlay_large_log_settings");
    };

    const setOverlayLargeLogSettings = (overlay_large_log_settings) => {
        // pendingOverlayLargeLogSettings();
        asyncStdoutToPython("/set/data/overlay_large_log_settings", overlay_large_log_settings);
    };


    const getOverlayShowOnlyTranslatedMessages = () => {
        pendingOverlayShowOnlyTranslatedMessages();
        asyncStdoutToPython("/get/data/overlay_show_only_translated_messages");
    };

    const toggleOverlayShowOnlyTranslatedMessages = () => {
        pendingOverlayShowOnlyTranslatedMessages();
        if (currentOverlayShowOnlyTranslatedMessages.data) {
            asyncStdoutToPython("/set/disable/overlay_show_only_translated_messages");
        } else {
            asyncStdoutToPython("/set/enable/overlay_show_only_translated_messages");
        }
    };


    const sendTextToOverlay = (text) => {
        asyncStdoutToPython("/run/send_text_overlay", text);
    };


    return {
        currentIsEnabledOverlaySmallLog,
        getIsEnabledOverlaySmallLog,
        updateIsEnabledOverlaySmallLog,
        toggleIsEnabledOverlaySmallLog,

        currentIsEnabledOverlayLargeLog,
        getIsEnabledOverlayLargeLog,
        updateIsEnabledOverlayLargeLog,
        toggleIsEnabledOverlayLargeLog,

        currentOverlaySmallLogSettings,
        getOverlaySmallLogSettings,
        updateOverlaySmallLogSettings,
        setOverlaySmallLogSettings,

        currentOverlayLargeLogSettings,
        getOverlayLargeLogSettings,
        updateOverlayLargeLogSettings,
        setOverlayLargeLogSettings,

        currentOverlayShowOnlyTranslatedMessages,
        getOverlayShowOnlyTranslatedMessages,
        updateOverlayShowOnlyTranslatedMessages,
        toggleOverlayShowOnlyTranslatedMessages,

        sendTextToOverlay,
    };
};