import { useI18n } from "@useI18n";
import styles from "./Others.module.scss";

import {
    useOpenFolder,
    useIsOscAvailable,
} from "@logics_common";

import {
    useOthers,
} from "@logics_configs";

import {
    CheckboxContainer,
    MessageFormatContainer,
} from "../_templates/Templates";

import {
    LabelComponent,
    ActionButton,
    SectionLabelComponent,
} from "../_components";
import { Checkbox } from "@common_components";

import OpenFolderSvg from "@images/open_folder.svg?react";

export const Others = () => {
    const { t } = useI18n();

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
                <SectionLabelComponent label={t("config_page.others.section_label_sounds")} />
                <EnableNotificationVrcSfxContainer />
            </div>
            <div>
                <SectionLabelComponent label="Speaker2Chatbox" />
                <SendReceivedMessageToVrcContainer />
            </div>
            <div>
                <SectionLabelComponent label={t("config_page.others.section_label_message_formats")} />
                <SendMessageFormatPartsContainer />
                <ReceivedMessageFormatPartsContainer />
            </div>
            <div>
                <ConvertMessageToRomajiContainer />
                <ConvertMessageToHiraganaContainer />
            </div>
        </div>
    );
};

const AutoClearMessageInputBoxContainer = () => {
    const { t } = useI18n();
    const { currentEnableAutoClearMessageInputBox, toggleEnableAutoClearMessageInputBox } = useOthers();

    return (
        <CheckboxContainer
            label={t("config_page.others.auto_clear_the_message_box.label")}
            variable={currentEnableAutoClearMessageInputBox}
            toggleFunction={toggleEnableAutoClearMessageInputBox}
        />
    );
};
const SendOnlyTranslatedMessagesContainer = () => {
    const { t } = useI18n();
    const { currentEnableSendOnlyTranslatedMessages, toggleEnableSendOnlyTranslatedMessages } = useOthers();

    return (
        <CheckboxContainer
            label={t("config_page.others.send_only_translated_messages.label")}
            variable={currentEnableSendOnlyTranslatedMessages}
            toggleFunction={toggleEnableSendOnlyTranslatedMessages}
        />
    );
};
const AutoExportMessageLogsContainer = () => {
    const { t } = useI18n();
    const { currentEnableAutoExportMessageLogs, toggleEnableAutoExportMessageLogs } = useOthers();
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
    const { t } = useI18n();
    const { currentEnableVrcMicMuteSync, toggleEnableVrcMicMuteSync } = useOthers();
    const { currentIsOscAvailable } = useIsOscAvailable();

    return (
        <CheckboxContainer
            label={t("config_page.others.vrc_mic_mute_sync.label")}
            desc={t("config_page.others.vrc_mic_mute_sync.desc")}
            variable={currentEnableVrcMicMuteSync}
            is_available={currentIsOscAvailable.data}
            toggleFunction={toggleEnableVrcMicMuteSync}
        />
    );
};
const SendMessageToVrcContainer = () => {
    const { t } = useI18n();
    const { currentEnableSendMessageToVrc, toggleEnableSendMessageToVrc } = useOthers();

    return (
        <CheckboxContainer
            label={t("config_page.others.send_message_to_vrc.label")}
            desc={t("config_page.others.send_message_to_vrc.desc")}
            variable={currentEnableSendMessageToVrc}
            toggleFunction={toggleEnableSendMessageToVrc}
        />
    );
};


const EnableNotificationVrcSfxContainer = () => {
    const { t } = useI18n();
    const { currentEnableNotificationVrcSfx, toggleEnableNotificationVrcSfx } = useOthers();

    return (
        <CheckboxContainer
            label={t("config_page.others.notification_vrc_sfx.label")}
            desc={t("config_page.others.notification_vrc_sfx.desc")}
            variable={currentEnableNotificationVrcSfx}
            toggleFunction={toggleEnableNotificationVrcSfx}
        />
    );
};

const SendReceivedMessageToVrcContainer = () => {
    const { t } = useI18n();
    const { currentEnableSendReceivedMessageToVrc, toggleEnableSendReceivedMessageToVrc } = useOthers();

    return (
        <CheckboxContainer
            label={t("config_page.others.send_received_message_to_vrc.label")}
            desc={t("config_page.others.send_received_message_to_vrc.desc")}
            variable={currentEnableSendReceivedMessageToVrc}
            toggleFunction={toggleEnableSendReceivedMessageToVrc}
        />
    );
};

const SendMessageFormatPartsContainer = () => {
    const { t } = useI18n();
    const {
        currentSendMessageFormatParts,
        setSendMessageFormatParts,
    } = useOthers();

    return (
        <MessageFormatContainer
            label={t("config_page.others.send_message_format.label")}
            desc={t("config_page.others.send_message_format.desc")}
            variable={currentSendMessageFormatParts}
            setFunction={setSendMessageFormatParts}
            format_id="send"
        />
    );
};

const ReceivedMessageFormatPartsContainer = () => {
    const { t } = useI18n();
    const {
        currentReceivedMessageFormatParts,
        setReceivedMessageFormatParts,
    } = useOthers();

    return (
        <MessageFormatContainer
            label={t("config_page.others.received_message_format.label")}
            desc={t("config_page.others.received_message_format.desc")}
            variable={currentReceivedMessageFormatParts}
            setFunction={setReceivedMessageFormatParts}
            format_id="received"
        />
    );
};

const ConvertMessageToRomajiContainer = () => {
    const { t } = useI18n();
    const { currentConvertMessageToRomaji, toggleConvertMessageToRomaji } = useOthers();

    const desc_1 = t("config_page.others.common_convert_message_hiragana_romaji.desc_1");
    const desc_2 = t("config_page.others.common_convert_message_hiragana_romaji.desc_2");
    const desc_romaji = t(
        "config_page.others.convert_message_to_romaji.desc",
        { convert_message_to_hiragana: t("config_page.others.convert_message_to_hiragana.label") }
    );
    const desc = [desc_1, desc_2, desc_romaji].join("\n");

    return (
        <CheckboxContainer
            label={t("config_page.others.convert_message_to_romaji.label")}
            desc={desc}
            variable={currentConvertMessageToRomaji}
            toggleFunction={toggleConvertMessageToRomaji}
        />
    );
};

const ConvertMessageToHiraganaContainer = () => {
    const { t } = useI18n();
    const { currentConvertMessageToHiragana, toggleConvertMessageToHiragana } = useOthers();

    const desc_1 = t("config_page.others.common_convert_message_hiragana_romaji.desc_1");
    const desc_2 = t("config_page.others.common_convert_message_hiragana_romaji.desc_2");
    const desc = [desc_1, desc_2].join("\n");

    return (
        <CheckboxContainer
            label={t("config_page.others.convert_message_to_hiragana.label")}
            desc={desc}
            variable={currentConvertMessageToHiragana}
            toggleFunction={toggleConvertMessageToHiragana}
        />
    );
};