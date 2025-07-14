import {
    useStore_EnableAutoClearMessageInputBox,
    useStore_EnableSendOnlyTranslatedMessages,
    useStore_EnableAutoExportMessageLogs,
    useStore_EnableVrcMicMuteSync,
    useStore_EnableSendMessageToVrc,
    useStore_EnableNotificationVrcSfx,
    useStore_EnableSendReceivedMessageToVrc,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useNotificationStatus } from "@logics_common";

export const useOthers = () => {
    const { asyncStdoutToPython } = useStdoutToPython();

    // Auto Clear Message Input Box
    const { currentEnableAutoClearMessageInputBox, updateEnableAutoClearMessageInputBox, pendingEnableAutoClearMessageInputBox } = useStore_EnableAutoClearMessageInputBox();
    // Send Only Translated Messages
    const { currentEnableSendOnlyTranslatedMessages, updateEnableSendOnlyTranslatedMessages, pendingEnableSendOnlyTranslatedMessages } = useStore_EnableSendOnlyTranslatedMessages();
    // Auto Export Message Logs
    const { currentEnableAutoExportMessageLogs, updateEnableAutoExportMessageLogs, pendingEnableAutoExportMessageLogs } = useStore_EnableAutoExportMessageLogs();
    // VRC Mic Mute Sync
    const { currentEnableVrcMicMuteSync, updateEnableVrcMicMuteSync, pendingEnableVrcMicMuteSync } = useStore_EnableVrcMicMuteSync();
    // Send Message To VRCT
    const { currentEnableSendMessageToVrc, updateEnableSendMessageToVrc, pendingEnableSendMessageToVrc } = useStore_EnableSendMessageToVrc();
    // Sounds
    // Notification VRC SFX
    const { currentEnableNotificationVrcSfx, updateEnableNotificationVrcSfx, pendingEnableNotificationVrcSfx } = useStore_EnableNotificationVrcSfx();
    // Speaker2Chatbox
    // Send Received Message To VRC
    const { currentEnableSendReceivedMessageToVrc, updateEnableSendReceivedMessageToVrc, pendingEnableSendReceivedMessageToVrc } = useStore_EnableSendReceivedMessageToVrc();

    const { showNotification_SaveSuccess } = useNotificationStatus();

    // Auto Clear Message Input Box
    const getEnableAutoClearMessageInputBox = () => {
        pendingEnableAutoClearMessageInputBox();
        asyncStdoutToPython("/get/data/auto_clear_message_box");
    };

    const toggleEnableAutoClearMessageInputBox = () => {
        pendingEnableAutoClearMessageInputBox();
        if (currentEnableAutoClearMessageInputBox.data) {
            asyncStdoutToPython("/set/disable/auto_clear_message_box");
        } else {
            asyncStdoutToPython("/set/enable/auto_clear_message_box");
        }
    };

    const setSuccessEnableAutoClearMessageInputBox = (enabled) => {
        updateEnableAutoClearMessageInputBox(enabled);
        showNotification_SaveSuccess();
    };

    // Send Only Translated Messages
    const getEnableSendOnlyTranslatedMessages = () => {
        pendingEnableSendOnlyTranslatedMessages();
        asyncStdoutToPython("/get/data/send_only_translated_messages");
    };

    const toggleEnableSendOnlyTranslatedMessages = () => {
        pendingEnableSendOnlyTranslatedMessages();
        if (currentEnableSendOnlyTranslatedMessages.data) {
            asyncStdoutToPython("/set/disable/send_only_translated_messages");
        } else {
            asyncStdoutToPython("/set/enable/send_only_translated_messages");
        }
    };

    const setSuccessEnableSendOnlyTranslatedMessages = (enabled) => {
        updateEnableSendOnlyTranslatedMessages(enabled);
        showNotification_SaveSuccess();
    };

    // Auto Export Message Logs
    const getEnableAutoExportMessageLogs = () => {
        pendingEnableAutoExportMessageLogs();
        asyncStdoutToPython("/get/data/logger_feature");
    };

    const toggleEnableAutoExportMessageLogs = () => {
        pendingEnableAutoExportMessageLogs();
        if (currentEnableAutoExportMessageLogs.data) {
            asyncStdoutToPython("/set/disable/logger_feature");
        } else {
            asyncStdoutToPython("/set/enable/logger_feature");
        }
    };

    const setSuccessEnableAutoExportMessageLogs = (enabled) => {
        updateEnableAutoExportMessageLogs(enabled);
        showNotification_SaveSuccess();
    };

    // VRC Mic Mute Sync
    const getEnableVrcMicMuteSync = () => {
        pendingEnableVrcMicMuteSync();
        asyncStdoutToPython("/get/data/vrc_mic_mute_sync");
    };

    const toggleEnableVrcMicMuteSync = () => {
        pendingEnableVrcMicMuteSync();
        if (currentEnableVrcMicMuteSync.data.is_enabled) {
            asyncStdoutToPython("/set/disable/vrc_mic_mute_sync");
        } else {
            asyncStdoutToPython("/set/enable/vrc_mic_mute_sync");
        }
    };

    const getSuccessEnableVrcMicMuteSync = (is_enabled) => {
        updateEnableVrcMicMuteSync(old => ({ ...old.data, is_enabled: is_enabled }));
    };

    const setSuccessEnableVrcMicMuteSync = (is_enabled) => {
        updateEnableVrcMicMuteSync(old => ({ ...old.data, is_enabled: is_enabled }));
        showNotification_SaveSuccess();
    };

    // Send Message To VRCT
    const getEnableSendMessageToVrc = () => {
        pendingEnableSendMessageToVrc();
        asyncStdoutToPython("/get/data/send_message_to_vrc");
    };

    const toggleEnableSendMessageToVrc = () => {
        pendingEnableSendMessageToVrc();
        if (currentEnableSendMessageToVrc.data) {
            asyncStdoutToPython("/set/disable/send_message_to_vrc");
        } else {
            asyncStdoutToPython("/set/enable/send_message_to_vrc");
        }
    };

    const setSuccessEnableSendMessageToVrc = (enabled) => {
        updateEnableSendMessageToVrc(enabled);
        showNotification_SaveSuccess();
    };

    // Sounds
    // Notification VRC SFX
    const getEnableNotificationVrcSfx = () => {
        pendingEnableNotificationVrcSfx();
        asyncStdoutToPython("/get/data/notification_vrc_sfx");
    };

    const toggleEnableNotificationVrcSfx = () => {
        pendingEnableNotificationVrcSfx();
        if (currentEnableNotificationVrcSfx.data) {
            asyncStdoutToPython("/set/disable/notification_vrc_sfx");
        } else {
            asyncStdoutToPython("/set/enable/notification_vrc_sfx");
        }
    };

    const setSuccessEnableNotificationVrcSfx = (enabled) => {
        updateEnableNotificationVrcSfx(enabled);
        showNotification_SaveSuccess();
    };

    // Speaker2Chatbox
    // Send Received Message To VRC
    const getEnableSendReceivedMessageToVrc = () => {
        pendingEnableSendReceivedMessageToVrc();
        asyncStdoutToPython("/get/data/send_received_message_to_vrc");
    };

    const toggleEnableSendReceivedMessageToVrc = () => {
        pendingEnableSendReceivedMessageToVrc();
        if (currentEnableSendReceivedMessageToVrc.data) {
            asyncStdoutToPython("/set/disable/send_received_message_to_vrc");
        } else {
            asyncStdoutToPython("/set/enable/send_received_message_to_vrc");
        }
    };

    const setSuccessEnableSendReceivedMessageToVrc = (enabled) => {
        updateEnableSendReceivedMessageToVrc(enabled);
        showNotification_SaveSuccess();
    };

    return {
        // Auto Clear Message Input Box
        currentEnableAutoClearMessageInputBox,
        getEnableAutoClearMessageInputBox,
        toggleEnableAutoClearMessageInputBox,
        updateEnableAutoClearMessageInputBox,
        setSuccessEnableAutoClearMessageInputBox,

        // Send Only Translated Messages
        currentEnableSendOnlyTranslatedMessages,
        getEnableSendOnlyTranslatedMessages,
        toggleEnableSendOnlyTranslatedMessages,
        updateEnableSendOnlyTranslatedMessages,
        setSuccessEnableSendOnlyTranslatedMessages,

        // Auto Export Message Logs
        currentEnableAutoExportMessageLogs,
        getEnableAutoExportMessageLogs,
        toggleEnableAutoExportMessageLogs,
        updateEnableAutoExportMessageLogs,
        setSuccessEnableAutoExportMessageLogs,

        // VRC Mic Mute Sync
        currentEnableVrcMicMuteSync,
        getEnableVrcMicMuteSync,
        getSuccessEnableVrcMicMuteSync,
        toggleEnableVrcMicMuteSync,
        updateEnableVrcMicMuteSync,
        setSuccessEnableVrcMicMuteSync,

        // Send Message To VRCT
        currentEnableSendMessageToVrc,
        getEnableSendMessageToVrc,
        toggleEnableSendMessageToVrc,
        updateEnableSendMessageToVrc,
        setSuccessEnableSendMessageToVrc,

        // Sounds
        // Notification VRC SFX
        currentEnableNotificationVrcSfx,
        getEnableNotificationVrcSfx,
        toggleEnableNotificationVrcSfx,
        updateEnableNotificationVrcSfx,
        setSuccessEnableNotificationVrcSfx,

        // Speaker2Chatbox
        // Send Received Message To VRC
        currentEnableSendReceivedMessageToVrc,
        getEnableSendReceivedMessageToVrc,
        toggleEnableSendReceivedMessageToVrc,
        updateEnableSendReceivedMessageToVrc,
        setSuccessEnableSendReceivedMessageToVrc,
    };
};