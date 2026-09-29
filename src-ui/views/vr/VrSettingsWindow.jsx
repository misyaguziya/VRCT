import { useState } from "react";
import clsx from "clsx";

import { useI18n } from "@useI18n";
import { useIsOpenedConfigPage, useIsOscAvailable, useVolume } from "@logics_common";
import { useDevice, useOcr, useOthers, useTranscription, useTranslation, useVr } from "@logics_configs";
import { useStore_MicVolume, useStore_SpeakerVolume } from "@store";
import { ui_configs } from "@ui_configs";

import HmdSvg from "@images/mui_head_mounted_device.svg?react";
import MicSvg from "@images/mic.svg?react";
import HeadphonesSvg from "@images/headphones.svg?react";
import TranslationSvg from "@images/translation.svg?react";
import GraphicEqSvg from "@images/mui_graphic_eq.svg?react";
import DiscoverTuneSvg from "@images/mui_discover_tune.svg?react";
import ChatTranscribeSvg from "@images/chat_transcribe.svg?react";
import WarningSvg from "@images/warning.svg?react";

import { VrWindow } from "./VrWindow";
import { Picker, SectionLabel, SegmentRow, SelectRow, StepperRow, ThresholdRow, ToggleRow } from "./VrSettingsRows";
import styles from "./VrSettingsWindow.module.scss";

// 左のカテゴリはデスクトップの設定画面と同じ名前・アイコン。VRでは文字入力が要る項目
// (APIキー、URL、単語フィルターなど) と、モデルのダウンロードは載せない
const CATEGORIES = [
    { id: "device", Icon: MicSvg },
    { id: "transcription", Icon: GraphicEqSvg },
    { id: "translation", Icon: TranslationSvg },
    { id: "vr", Icon: HmdSvg },
    { id: "others", Icon: DiscoverTuneSvg },
    { id: "ocr", Icon: ChatTranscribeSvg },
];

// 翻訳のAIのうち、接続済み (モデルの一覧が取れている) ものだけモデルを選べる
const AI_PROVIDERS = [
    { key: "Plamo", i18n: "plamo" },
    { key: "Gemini", i18n: "gemini" },
    { key: "OpenAI", i18n: "openai" },
    { key: "Groq", i18n: "groq" },
    { key: "OpenRouter", i18n: "openrouter" },
    { key: "LMStudio", i18n: "lmstudio" },
    { key: "OpenAICompatible", i18n: "openai_compatible" },
    { key: "Ollama", i18n: "ollama" },
];

const THRESHOLD_STEP = 50;
// 一覧 ({ id: label }) を Picker の形にする
const toOptions = (list) => Object.entries(list ?? {}).map(([id, label]) => ({ id, label }));

// VR設定ウィンドウ。開いている間はデスクトップで設定画面を開いたのと同じ扱いで、
// 翻訳と文字起こしが止まる (VrApp / VrPanelSyncController)
export const VrSettingsWindow = ({ onClose }) => {
    const { t } = useI18n();
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const [category, setCategory] = useState("device");
    // 選択肢の一覧を開いているとき: { title, options, selected_id, onPick }
    const [picker, setPicker] = useState(null);

    // メインが設定画面を開いてメイン機能を止めるまでは操作させない (音量の確認がマイクを奪い合わないように)
    const is_ready = currentIsOpenedConfigPage.data === true;
    const openPicker = (title, options, selected_id, onPick) => setPicker({ title, options, selected_id, onPick });

    const category_label = (id) => (id === "vr" ? "VR" : t(`config_page.side_menu_labels.${id}`));

    return (
        <VrWindow Icon={HmdSvg} title={t("vr_panel.window_settings")} onClose={onClose} is_lockable={false}>
            <div className={styles.window_body}>
                <p className={styles.banner}>
                    <WarningSvg className={styles.banner_icon} />
                    {t("vr_panel.paused_while_settings")}
                </p>
                <div className={clsx(styles.body, { [styles.is_waiting]: !is_ready })}>
                    <div className={styles.side}>
                        {CATEGORIES.map(({ id, Icon }) => (
                            <button key={id}
                                className={clsx(styles.button, styles.category, { [styles.is_selected]: id === category })}
                                onClick={() => { setCategory(id); setPicker(null); }}
                            >
                                <Icon className={styles.category_icon} />
                                <span className={styles.category_label}>{category_label(id)}</span>
                            </button>
                        ))}
                    </div>
                    {/* key でカテゴリを切り替えるたびにスクロール位置を先頭へ戻す */}
                    <div key={`${category}/${picker?.title ?? ""}`} className={styles.list}>
                        {picker
                            ? <Picker {...picker} back_label={t("common.go_back_button_label")}
                                onPick={(id) => { picker.onPick(id); setPicker(null); }}
                                onBack={() => setPicker(null)} />
                            : <Category id={category} t={t} openPicker={openPicker} />
                        }
                    </div>
                </div>
            </div>
        </VrWindow>
    );
};

const Category = ({ id, t, openPicker }) => {
    switch (id) {
        case "device": return <DeviceSettings t={t} openPicker={openPicker} />;
        case "transcription": return <TranscriptionSettings t={t} openPicker={openPicker} />;
        case "translation": return <TranslationSettings t={t} openPicker={openPicker} />;
        case "vr": return <VrSettings t={t} />;
        case "others": return <OthersSettings t={t} />;
        case "ocr": return <OcrSettings t={t} openPicker={openPicker} />;
        default: return null;
    }
};

const DeviceSettings = ({ t, openPicker }) => {
    const d = useDevice();
    const v = useVolume();
    const { currentMicVolume } = useStore_MicVolume();
    const { currentSpeakerVolume } = useStore_SpeakerVolume();
    // 機器の選択はデスクトップと同じく、自動選択がONの間 (と切り替え中) は押せない
    const deviceRow = (label, list, selected, setSelected, auto_select) => (
        <SelectRow label={label} value={list.data?.[selected.data] ?? selected.data}
            is_pending={selected.state === "pending"}
            is_disabled={auto_select.data === true || auto_select.state === "pending"}
            onOpen={() => openPicker(label, toOptions(list.data), selected.data, setSelected)} />
    );
    return (
        <>
            <SectionLabel label={t("config_page.device.mic_host_device.label")} />
            <ToggleRow label={t("config_page.device.label_auto_select")}
                variable={d.currentEnableAutoMicSelect} onToggle={d.toggleEnableAutoMicSelect} />
            {deviceRow(t("config_page.device.label_host"), d.currentMicHostList, d.currentSelectedMicHost, d.setSelectedMicHost, d.currentEnableAutoMicSelect)}
            {deviceRow(t("config_page.device.label_device"), d.currentMicDeviceList, d.currentSelectedMicDevice, d.setSelectedMicDevice, d.currentEnableAutoMicSelect)}
            <ThresholdRow
                label={t("vr_panel.mic_threshold")} automatic_label={t("vr_panel.automatic")} CheckIcon={MicSvg}
                threshold={d.currentMicThreshold} setThreshold={d.setMicThreshold}
                automatic={d.currentEnableAutomaticMicThreshold} toggleAutomatic={d.toggleEnableAutomaticMicThreshold}
                check_status={v.currentMicThresholdCheckStatus} startCheck={v.volumeCheckStart_Mic} stopCheck={v.volumeCheckStop_Mic}
                volume={currentMicVolume.data}
                min={ui_configs.mic_threshold_min} max={ui_configs.mic_threshold_max} step={THRESHOLD_STEP}
            />
            <SectionLabel label={t("config_page.device.speaker_device.label")} />
            <ToggleRow label={t("config_page.device.label_auto_select")}
                variable={d.currentEnableAutoSpeakerSelect} onToggle={d.toggleEnableAutoSpeakerSelect} />
            {deviceRow(t("config_page.device.label_device"), d.currentSpeakerDeviceList, d.currentSelectedSpeakerDevice, d.setSelectedSpeakerDevice, d.currentEnableAutoSpeakerSelect)}
            <ThresholdRow
                label={t("vr_panel.speaker_threshold")} automatic_label={t("vr_panel.automatic")} CheckIcon={HeadphonesSvg}
                threshold={d.currentSpeakerThreshold} setThreshold={d.setSpeakerThreshold}
                automatic={d.currentEnableAutomaticSpeakerThreshold} toggleAutomatic={d.toggleEnableAutomaticSpeakerThreshold}
                check_status={v.currentSpeakerThresholdCheckStatus} startCheck={v.volumeCheckStart_Speaker} stopCheck={v.volumeCheckStop_Speaker}
                volume={currentSpeakerVolume.data}
                min={ui_configs.speaker_threshold_min} max={ui_configs.speaker_threshold_max} step={THRESHOLD_STEP}
            />
        </>
    );
};

const TranscriptionSettings = ({ t, openPicker }) => {
    const tr = useTranscription();
    const engines = [{ id: "Google", label: "Google" }, { id: "Whisper", label: "Whisper" }];
    const engine_label = t("config_page.transcription.select_transcription_engine.label");
    // 区切りの秒数は「記録の上限 ≦ 無音で区切る秒数」でないとバックエンドが受け付けない
    const timeoutRows = (prefix, max_words) => {
        const record = tr[`current${prefix}RecordTimeout`];
        const phrase = tr[`current${prefix}PhraseTimeout`];
        const lower = prefix.toLowerCase();
        return (
            <>
                <SectionLabel label={t(`config_page.transcription.section_label_${lower}`)} />
                <StepperRow label={t(`config_page.transcription.${lower}_record_timeout.label`)}
                    variable={record} setValue={tr[`set${prefix}RecordTimeout`]} min={0} max={Math.min(30, Number(phrase.data))} step={1} />
                <StepperRow label={t(`config_page.transcription.${lower}_phrase_timeout.label`)}
                    variable={phrase} setValue={tr[`set${prefix}PhraseTimeout`]} min={Number(record.data)} max={30} step={1} />
                <StepperRow label={t(`config_page.transcription.${lower}_max_phrase.label`)}
                    variable={tr[`current${prefix}MaxWords`]} setValue={tr[`set${prefix}MaxWords`]} min={0} max={max_words} step={1} />
            </>
        );
    };
    return (
        <>
            <SelectRow label={engine_label} value={tr.currentSelectedTranscriptionEngine.data}
                is_pending={tr.currentSelectedTranscriptionEngine.state === "pending"}
                onOpen={() => openPicker(engine_label, engines, tr.currentSelectedTranscriptionEngine.data, tr.setSelectedTranscriptionEngine)} />
            {timeoutRows("Mic", 30)}
            {timeoutRows("Speaker", 60)}
        </>
    );
};

const TranslationSettings = ({ t, openPicker }) => {
    const tl = useTranslation();
    // CTranslate2 はダウンロード済みのモデルだけ選べる (ダウンロードはデスクトップで行う)
    const weights = tl.currentCTranslate2WeightTypeStatus.data
        .filter(w => w.is_downloaded)
        .map(w => ({ id: w.id, label: `${w.id} (${w.capacity})` }));
    const ct2_label = t("config_page.translation.ctranslate2_weight_type.label", { ctranslate2: "CTranslate2" });
    const selected_weight = tl.currentSelectedCTranslate2WeightType;
    return (
        <>
            <SelectRow label={ct2_label} value={selected_weight.data} is_pending={selected_weight.state === "pending"}
                onOpen={() => openPicker(ct2_label, weights, selected_weight.data, tl.setSelectedCTranslate2WeightType)} />
            {AI_PROVIDERS.map(({ key, i18n }) => {
                const options = toOptions(tl[`currentSelectable${key}ModelList`].data);
                if (options.length === 0) return null;
                const selected = tl[`currentSelected${key}Model`];
                const label = t(`config_page.translation.select_${i18n}_model.label`);
                return (
                    <SelectRow key={key} label={label} value={selected.data} is_pending={selected.state === "pending"}
                        onOpen={() => openPicker(label, options, selected.data, tl[`setSelected${key}Model`])} />
                );
            })}
        </>
    );
};

const VrSettings = ({ t }) => {
    const vr = useVr();
    const opacity = vr.currentOverlayVrPanelOpacity;
    // VR UI 自体のON/OFFはここに置かない (VRの中で消すと戻せなくなる。デスクトップの設定で行う)
    return (
        <>
            <ToggleRow label={t("vr_panel.overlay_small_log")} variable={vr.currentIsEnabledOverlaySmallLog}
                onToggle={vr.toggleIsEnabledOverlaySmallLog} />
            <ToggleRow label={t("vr_panel.overlay_large_log")} variable={vr.currentIsEnabledOverlayLargeLog}
                onToggle={vr.toggleIsEnabledOverlayLargeLog} />
            <ToggleRow label={t("config_page.vr.overlay_show_only_translated_messages.label")}
                variable={vr.currentOverlayShowOnlyTranslatedMessages} onToggle={vr.toggleOverlayShowOnlyTranslatedMessages} />
            <StepperRow label={t("vr_panel.log_opacity")} variable={opacity} setValue={vr.setOverlayVrPanelOpacity}
                min={0.2} max={1.0} step={0.1} format={(v) => `${Math.round(v * 100)}%`} />
            <SectionLabel label={t("vr_panel.launcher")} />
            <SegmentRow label={t("vr_panel.launcher_hand")} sub={t("vr_panel.launcher_hand_desc")}
                variable={vr.currentOverlayVrLauncherHand} onSelect={vr.setOverlayVrLauncherHand}
                options={[
                    { id: "LeftHand", label: t("vr_panel.anchor_left_hand") },
                    { id: "RightHand", label: t("vr_panel.anchor_right_hand") },
                ]} />
            <ToggleRow label={t("vr_panel.launcher_auto_hide")} sub={t("vr_panel.launcher_auto_hide_desc")}
                variable={vr.currentOverlayVrLauncherAutoHide} onToggle={vr.toggleOverlayVrLauncherAutoHide} />
            <StepperRow label={t("vr_panel.launcher_hide_angle")} sub={t("vr_panel.launcher_hide_angle_desc")}
                variable={vr.currentOverlayVrLauncherHideAngle} setValue={vr.setOverlayVrLauncherHideAngle}
                min={15} max={90} step={5} format={(v) => `${v}°`}
                is_disabled={vr.currentOverlayVrLauncherAutoHide.data !== true} />
        </>
    );
};

const OthersSettings = ({ t }) => {
    const o = useOthers();
    const { currentIsOscAvailable } = useIsOscAvailable();
    const toggle = (name, key) => (
        <ToggleRow label={t(`config_page.others.${key}.label`)} variable={o[`current${name}`]} onToggle={o[`toggle${name}`]} />
    );
    const is_osc_unavailable = currentIsOscAvailable.data === false;
    return (
        <>
            {toggle("EnableSendMessageToVrc", "send_message_to_vrc")}
            {toggle("EnableSendOnlyTranslatedMessages", "send_only_translated_messages")}
            {toggle("EnableSendReceivedMessageToVrc", "send_received_message_to_vrc")}
            {toggle("EnableNotificationVrcSfx", "notification_vrc_sfx")}
            <ToggleRow label={t("config_page.others.vrc_mic_mute_sync.label")}
                variable={o.currentEnableVrcMicMuteSync} onToggle={o.toggleEnableVrcMicMuteSync}
                is_disabled={is_osc_unavailable}
                sub={is_osc_unavailable ? t("config_page.common.warning_labels.unable_to_use_osc_query") : null} />
            {toggle("ConvertMessageToRomaji", "convert_message_to_romaji")}
            {toggle("ConvertMessageToHiragana", "convert_message_to_hiragana")}
        </>
    );
};

// チャット読み取りのON/OFFは機能の切り替えなので、ここには置かない (ランチャーで行う)
const OcrSettings = ({ t, openPicker }) => {
    const ocr = useOcr();
    const languages = ocr.currentSelectableOcrSourceLanguageList.data ?? {};
    const language = ocr.currentOcrSourceLanguage;
    const language_label = t("config_page.ocr.source_language.label");
    return (
        <>
            <SelectRow label={language_label} value={languages[language.data] ?? language.data}
                is_pending={language.state === "pending"}
                onOpen={() => openPicker(language_label, toOptions(languages), language.data, ocr.setOcrSourceLanguage)} />
            <StepperRow label={t("config_page.ocr.poll_interval_ms.label")} variable={ocr.currentOcrPollIntervalMs}
                setValue={ocr.setOcrPollIntervalMs} min={100} max={5000} step={100} format={(v) => `${v} ms`} />
            <StepperRow label={t("config_page.ocr.min_confidence.label")} variable={ocr.currentOcrMinConfidence}
                setValue={ocr.setOcrMinConfidence} min={0.1} max={0.99} step={0.05} format={(v) => v.toFixed(2)} />
            <StepperRow label={t("config_page.ocr.bubble_min_text_length.label")} variable={ocr.currentOcrBubbleMinTextLength}
                setValue={ocr.setOcrBubbleMinTextLength} min={1} max={50} step={1} />
        </>
    );
};
