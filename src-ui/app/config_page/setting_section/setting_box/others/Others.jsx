import { useTranslation } from "react-i18next";
import styles from "./Others.module.scss";

import { useOpenFolder } from "@logics_common";
import {
    useEnableAutoClearMessageInputBox,
    useEnableSendOnlyTranslatedMessages,
    useEnableAutoExportMessageLogs,
    useEnableVrcMicMuteSync,
    useEnableSendMessageToVrc,
    useEnableSendReceivedMessageToVrc,
} from "@logics_configs";

import {
    CheckboxContainer,
} from "../_templates/Templates";

import {
    LabelComponent,
    Checkbox,
    ActionButton,
    SectionLabelComponent,
} from "../_components/";

import OpenFolderSvg from "@images/open_folder.svg?react";

export const Others = () => {
    return (
        <div className={styles.container}>
            <div>
                <AutoClearMessageInputBoxContainer />
                <SendOnlyTranslatedMessagesContainer />
                <AutoExportMessageLogsContainer />
                <VrcMicMuteSyncContainer />
                <SendMessageToVrcContainer />
            </div>
            <div>
                <SectionLabelComponent label="Speaker2Chatbox" />
                <SendReceivedMessageToVrcContainer />
            </div>
        </div>
    );
};

const AutoClearMessageInputBoxContainer = () => {
    const { t } = useTranslation();
    const { currentEnableAutoClearMessageInputBox, toggleEnableAutoClearMessageInputBox } = useEnableAutoClearMessageInputBox();

    return (
        <CheckboxContainer
            label={t("config_page.others.auto_clear_the_message_box.label")}
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
            label={t("config_page.others.send_only_translated_messages.label")}
            variable={currentEnableSendOnlyTranslatedMessages}
            toggleFunction={toggleEnableSendOnlyTranslatedMessages}
        />
    );
};
const AutoExportMessageLogsContainer = () => {
    const { t } = useTranslation();
    const { currentEnableAutoExportMessageLogs, toggleEnableAutoExportMessageLogs } = useEnableAutoExportMessageLogs();
    const { openFolder_MessageLogs } = useOpenFolder();

    return (
        <div className={styles.auto_export_message_logs_container}>
            <LabelComponent
                label={t("config_page.others.auto_export_message_logs.label")}
                desc={t("config_page.others.auto_export_message_logs.desc")}
                />
            <div className={styles.auto_export_message_logs_switch_section_container}>
                <ActionButton
                    IconComponent={OpenFolderSvg}
                    onclickFunction={openFolder_MessageLogs}
                />
                <Checkbox
                    variable={currentEnableAutoExportMessageLogs}
                    toggleFunction={toggleEnableAutoExportMessageLogs}
                />
            </div>
        </div>
    );
};
export const VrcMicMuteSyncContainer = () => {
    const { t } = useTranslation();
    const { currentEnableVrcMicMuteSync, toggleEnableVrcMicMuteSync } = useEnableVrcMicMuteSync();

    return (
        <CheckboxContainer
            label={t("config_page.others.vrc_mic_mute_sync.label")}
            desc={t("config_page.others.vrc_mic_mute_sync.desc")}
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
            label={t("config_page.others.send_message_to_vrc.label")}
            desc={t("config_page.others.send_message_to_vrc.desc")}
            variable={currentEnableSendMessageToVrc}
            toggleFunction={toggleEnableSendMessageToVrc}
        />
    );
};


const SendReceivedMessageToVrcContainer = () => {
    const { t } = useTranslation();
    const { currentEnableSendReceivedMessageToVrc, toggleEnableSendReceivedMessageToVrc } = useEnableSendReceivedMessageToVrc();

    return (
        <CheckboxContainer
            label={t("config_page.others.send_received_message_to_vrc.label")}
            desc={t("config_page.others.send_received_message_to_vrc.desc")}
            variable={currentEnableSendReceivedMessageToVrc}
            toggleFunction={toggleEnableSendReceivedMessageToVrc}
        />
    );
};