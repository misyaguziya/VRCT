import { useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { emit, listen } from "@tauri-apps/api/event";
import { getDefaultStore } from "jotai";

import { dynamicStoreRegistry } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useIsOpenedConfigPage, useVrPanelSteamVr } from "@logics_common";
import { useVr } from "@logics_configs";
import { encodeOrdered, isRelayAllowed } from "../../../logics/common/vrPanelWire";
import { VR_WINDOWS_PATH, configPageAfterVrPanelGone, rememberedVrWindows, vrPanelWindowWanted } from "../../../logics/common/vrPanelWindows";
import { isLanguageMutation, rejectLanguageMutation } from "../../../logics/main/languageMutations";

// VRパネル (vr_panel ウィンドウ) をこのウィンドウの完全なミラーにする。
// - 全atomの値をVRパネルへ一方向に同期する (機能が増えても個別の同期コードは不要)
// - VRパネルからのバックエンド送信を代わりに行う。設定画面を開いている間は
//   メイン機能を一時停止しているため (ConfigPageCloseTriggerController)、拒否する
// - VRのVR設定ウィンドウを開いている間は、デスクトップで設定画面を開いたのと同じ扱いにする
//   (メイン機能を止め、閉じたら戻す)。このときだけ設定画面中でもVRからの送信を通す
//   (VR側は設定ウィンドウ以外を操作できないようにしている)
const jotai = getDefaultStore();

const WINDOW_REQUEST_PATHS = [
    "/run/vr_panel_windows",
    "/run/vr_panel_recall_log",
    "/run/vr_panel_recall_keyboard",
    "/set/data/overlay_vr_panel_anchor",
    "/set/enable/overlay_vr_panel_locked",
    "/set/disable/overlay_vr_panel_locked",
    "/set/data/overlay_vr_panel_opacity",
    "/set/data/overlay_vr_panel_font_size",
    "/run/vr_panel_layout_rendered",
    "/run/vr_panel_tooltip",
    "/set/data/overlay_vr_panel_form",
    "/run/vr_panel_log_rendered",
    // 字幕の形の文字の大きさ (操作バーの A−/A＋、部分更新)
    "/set/data/overlay_vr_subtitle_settings",
];

const atomEntries = () => Object.entries(dynamicStoreRegistry)
    .filter(([key]) => key.startsWith("Atom_"))
    .map(([key, atom]) => [key.slice("Atom_".length), atom]);

// ponytail: 変化したatomは値を丸ごと送る (ログ配列も全件)。ログが数千件規模で重くなるなら差分送信にする
const emitState = (entries) => {
    const payload = {};
    for (const [name, atom] of entries) {
        const value = jotai.get(atom);
        try {
            JSON.stringify(value);
            payload[name] = encodeOrdered(value); // emit でキーが辞書順になるので、並びを保つ形で送る
        } catch {
            // DOM参照など、ウィンドウをまたいで送れない値は同期しない
        }
    }
    emit("vr-panel-state", payload);
};

export const VrPanelSyncController = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentIsOpenedConfigPage, setIsOpenedConfigPage } = useIsOpenedConfigPage();
    const { currentIsEnabledOverlayVrPanel } = useVr();

    // VR画面のウィンドウは VR UI が ON で SteamVR に一度つながったら作り、VR UI を OFF にするまで残す (SteamVR を
    // 使わない間に負荷をかけない。切れても作り直さない)。作られた VR画面は vr-panel-ready を送ってくるので、状態はそのときに送る
    const { currentVrPanelSteamVr } = useVrPanelSteamVr();
    const had_window = useRef(false);
    had_window.current = vrPanelWindowWanted(had_window.current, currentIsEnabledOverlayVrPanel.data === true, currentVrPanelSteamVr.data === true);
    const is_vr_panel_needed = had_window.current;
    useEffect(() => {
        invoke("set_vr_panel_window", { open: is_vr_panel_needed }).catch(console.error);
    }, [is_vr_panel_needed]);
    const isOpenedConfigPageRef = useRef(currentIsOpenedConfigPage.data);
    isOpenedConfigPageRef.current = currentIsOpenedConfigPage.data;
    // VRのVR設定ウィンドウを開いているか (開いている間はVRからの送信を通す)
    const isVrSettingsOpenRef = useRef(false);
    // 設定画面を開いたのがVRか (VR設定ウィンドウを閉じたとき、設定画面も閉じてよいか)
    const isOpenedByVrRef = useRef(false);

    // デスクトップ側で設定画面が閉じられたら、VRの扱いも終わる (VR側は設定ウィンドウを閉じる)
    useEffect(() => {
        if (currentIsOpenedConfigPage.data !== true) {
            isVrSettingsOpenRef.current = false;
            isOpenedByVrRef.current = false;
        }
    }, [currentIsOpenedConfigPage.data]);

    // VR画面のウィンドウが無い間 (VR UI が OFF か SteamVR につながっていない) は、全atomの同期も VR画面からの
    // 要求の受付もしない (ログが数千件に育ってもメッセージごとに全件を直列化して送ることになるため)。作られたら全状態を送る
    useEffect(() => {
        if (!is_vr_panel_needed) return undefined;
        const entries = atomEntries();
        const unsubscribes = entries.map(([name, atom]) =>
            jotai.sub(atom, () => emitState([[name, atom]]))
        );
        const unlistenReady = listen("vr-panel-ready", () => emitState(atomEntries()));
        const unlistenStdout = listen("vr-panel-stdout", ({ payload }) => {
            if (!isRelayAllowed(payload.path)) {
                console.warn("[vr-panel] blocked request from the VR panel:", payload.path);
                rejectLanguageMutation(payload.languageRequest, "blocked");
                return;
            }
            // 開いている窓は覚えておく (VR 画面を作り直したときに開き直す)
            if (payload.path === VR_WINDOWS_PATH) {
                jotai.set(dynamicStoreRegistry.Atom_VrPanelWindows, { state: "ok", data: rememberedVrWindows(payload.value) });
            }
            // ウィンドウの開閉・呼び戻しと、ログの操作バー (固定先・ロック・不透明度) はメイン機能と関係ないので、
            // 設定画面を開いている間も通す
            const is_window_request = WINDOW_REQUEST_PATHS.includes(payload.path);
            const is_allowed = is_window_request || isVrSettingsOpenRef.current === true;
            if (isOpenedConfigPageRef.current === true && !is_allowed) {
                rejectLanguageMutation(payload.languageRequest, "config-open");
                // VRパネル側で pending にした表示を元に戻すため、状態を送り直す
                emitState(atomEntries());
                return;
            }
            asyncStdoutToPython(payload.path, payload.value, payload.languageRequest).then(sent => {
                if (sent === false && isLanguageMutation(payload.path)) emitState(atomEntries());
            }).catch(console.error);
        });
        const unlistenConfigPage = listen("vr-panel-config-page", ({ payload: is_opened }) => {
            if (is_opened === true) {
                isVrSettingsOpenRef.current = true;
                // デスクトップが先に開いていたら、VR側を閉じてもデスクトップの設定画面は閉じない
                if (isOpenedConfigPageRef.current !== true) isOpenedByVrRef.current = true;
                setIsOpenedConfigPage(true);
                return;
            }
            isVrSettingsOpenRef.current = false;
            // VRが開いたときだけ閉じる (VRの起動時などに届く false でデスクトップの設定画面を閉じない)
            if (isOpenedByVrRef.current === true) {
                isOpenedByVrRef.current = false;
                setIsOpenedConfigPage(false);
            }
        });
        // VRパネルが先に起動していた場合に備えて、こちらからも一度送る
        emitState(entries);

        return () => {
            unsubscribes.forEach(unsubscribe => unsubscribe());
            unlistenReady.then(f => f());
            unlistenStdout.then(f => f());
            unlistenConfigPage.then(f => f());
            // VR 画面の窓が無くなった (SteamVR の終了・VR UI の OFF): VR の設定ウィンドウが開いた設定画面は
            // 「閉じた」がもう届かないので、ここで閉じる (メイン機能が止まったままにならない)
            const config_page = configPageAfterVrPanelGone(isOpenedByVrRef.current);
            isVrSettingsOpenRef.current = false;
            isOpenedByVrRef.current = false;
            if (config_page !== null) setIsOpenedConfigPage(config_page);
        };
    }, [is_vr_panel_needed]);

    return null;
};
