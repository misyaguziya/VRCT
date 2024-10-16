import { useTranslation } from "react-i18next";

import {
    useEnableAutoClearMessageInputBox,
    useEnableSendOnlyTranslatedMessages,
    useEnableAutoExportMessageLogs,
    useEnableVrcMicMuteSync,
    useEnableSendMessageToVrc,
} from "@logics_configs";

import {
    CheckboxContainer,
} from "../_templates/Templates";


export const Others = () => {
    return (
        <>
            <AutoClearMessageInputBoxContainer />
            <SendOnlyTranslatedMessagesContainer />
            <AutoExportMessageLogsContainer />
            <VrcMicMuteSyncContainer />
            <SendMessageToVrcContainer />
        </>
    );
};

const AutoClearMessageInputBoxContainer = () => {
    const { t } = useTranslation();
    const { currentEnableAutoClearMessageInputBox, toggleEnableAutoClearMessageInputBox } = useEnableAutoClearMessageInputBox();

    return (
        <CheckboxContainer
            label={t("config_page.auto_clear_the_message_box.label")}
            variable={currentEnableAutoClearMessageInputBox}
            toggleFunction={toggleEnableAutoClearMessageInputBox}
        />
    );
};
const SendOnlyTranslatedMessagesContainer = () => {
    const { t } = useTranslation();
    const { currentEnableSendOnlyTranslatedMessages, toggleEnableSendOnlyTranslatedMessages } = useEnableSendOnlyTranslatedMessages();

    return (
        <CheckboxContainer
            label={t("config_page.send_only_translated_messages.label")}
            variable={currentEnableSendOnlyTranslatedMessages}
            toggleFunction={toggleEnableSendOnlyTranslatedMessages}
        />
    );
};
const AutoExportMessageLogsContainer = () => {
    const { t } = useTranslation();
    const { currentEnableAutoExportMessageLogs, toggleEnableAutoExportMessageLogs } = useEnableAutoExportMessageLogs();

    return (
        <CheckboxContainer
            label={t("config_page.auto_export_message_logs.label")}
            desc={t("config_page.auto_export_message_logs.desc")}
            variable={currentEnableAutoExportMessageLogs}
            toggleFunction={toggleEnableAutoExportMessageLogs}
        />
    );
};
const VrcMicMuteSyncContainer = () => {
    const { t } = useTranslation();
    const { currentEnableVrcMicMuteSync, toggleEnableVrcMicMuteSync } = useEnableVrcMicMuteSync();

    return (
        <CheckboxContainer
            label={t("config_page.vrc_mic_mute_sync.label")}
            desc={t("config_page.vrc_mic_mute_sync.desc")}
            variable={currentEnableVrcMicMuteSync}
            toggleFunction={toggleEnableVrcMicMuteSync}
        />
    );
};
const SendMessageToVrcContainer = () => {
    const { t } = useTranslation();
    const { currentEnableSendMessageToVrc, toggleEnableSendMessageToVrc } = useEnableSendMessageToVrc();

    return (
        <CheckboxContainer
            label={t("config_page.send_message_to_vrc.label")}
            desc={t("config_page.send_message_to_vrc.desc")}
            variable={currentEnableSendMessageToVrc}
            toggleFunction={toggleEnableSendMessageToVrc}
        />
    );
};