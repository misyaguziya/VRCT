import {
    useStore_IsEnabledOverlaySmallLog,
    useStore_IsEnabledOverlayLargeLog,
    useStore_OverlaySmallLogSettings,
    useStore_OverlayLargeLogSettings,
    useStore_OverlayShowOnlyTranslatedMessages,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useNotificationStatus } from "@logics_common";

export const useVr = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { showNotification_SaveSuccess } = useNotificationStatus();

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

    const setSuccessIsEnabledOverlaySmallLog = (enabled) => {
        updateIsEnabledOverlaySmallLog(enabled);
        showNotification_SaveSuccess();
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

    const setSuccessIsEnabledOverlayLargeLog = (enabled) => {
        updateIsEnabledOverlayLargeLog(enabled);
        showNotification_SaveSuccess();
    };

    const getOverlaySmallLogSettings = () => {
        // pendingOverlaySmallLogSettings();
        asyncStdoutToPython("/get/data/overlay_small_log_settings");
    };

    const setOverlaySmallLogSettings = (overlay_small_log_settings) => {
        // pendingOverlaySmallLogSettings();
        asyncStdoutToPython("/set/data/overlay_small_log_settings", overlay_small_log_settings);
    };

    const setSuccessOverlaySmallLogSettings = (settings) => {
        updateOverlaySmallLogSettings(settings);
        showNotification_SaveSuccess();
    };

    const getOverlayLargeLogSettings = () => {
        // pendingOverlayLargeLogSettings();
        asyncStdoutToPython("/get/data/overlay_large_log_settings");
    };

    const setOverlayLargeLogSettings = (overlay_large_log_settings) => {
        // pendingOverlayLargeLogSettings();
        asyncStdoutToPython("/set/data/overlay_large_log_settings", overlay_large_log_settings);
    };

    const setSuccessOverlayLargeLogSettings = (settings) => {
        updateOverlayLargeLogSettings(settings);
        showNotification_SaveSuccess();
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

    const setSuccessOverlayShowOnlyTranslatedMessages = (enabled) => {
        updateOverlayShowOnlyTranslatedMessages(enabled);
        showNotification_SaveSuccess();
    };

    const sendTextToOverlay = (text) => {
        asyncStdoutToPython("/run/send_text_overlay", text);
    };

    return {
        currentIsEnabledOverlaySmallLog,
        getIsEnabledOverlaySmallLog,
        toggleIsEnabledOverlaySmallLog,
        updateIsEnabledOverlaySmallLog,
        setSuccessIsEnabledOverlaySmallLog,

        currentIsEnabledOverlayLargeLog,
        getIsEnabledOverlayLargeLog,
        toggleIsEnabledOverlayLargeLog,
        updateIsEnabledOverlayLargeLog,
        setSuccessIsEnabledOverlayLargeLog,

        currentOverlaySmallLogSettings,
        getOverlaySmallLogSettings,
        updateOverlaySmallLogSettings,
        setOverlaySmallLogSettings,
        setSuccessOverlaySmallLogSettings,

        currentOverlayLargeLogSettings,
        getOverlayLargeLogSettings,
        updateOverlayLargeLogSettings,
        setOverlayLargeLogSettings,
        setSuccessOverlayLargeLogSettings,

        currentOverlayShowOnlyTranslatedMessages,
        getOverlayShowOnlyTranslatedMessages,
        toggleOverlayShowOnlyTranslatedMessages,
        updateOverlayShowOnlyTranslatedMessages,
        setSuccessOverlayShowOnlyTranslatedMessages,

        sendTextToOverlay,
    };
};