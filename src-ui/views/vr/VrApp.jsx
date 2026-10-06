import { useEffect, useRef, useState } from "react";
import { emit, listen } from "@tauri-apps/api/event";
import { getDefaultStore } from "jotai";

import { dynamicStoreRegistry } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useIsOpenedConfigPage } from "@logics_common";

import {
    UiLanguageController,
    FontFamilyController,
} from "../app/_app_controllers";

import { useVr } from "@logics_configs";
import { VrLauncher } from "./VrLauncher";
import { VrLogWindow } from "./VrLogWindow";
import { VrPopupWindow } from "./VrPopupWindow";
import { VrToolbar } from "./VrToolbar";
import { VrTooltip } from "./VrTooltip";
import { keepNewestVrLayout } from "../../logics/common/vrPanelTooltip";
import { decodeOrdered } from "../../logics/common/vrPanelWire";

import styles from "./VrApp.module.scss";

// VR UI は1枚の画面外ウィンドウ (vr_layout.json の atlas) に各ウィンドウを並べて描く。
// Python 側 (models/overlay/overlay.py) が1回だけ撮影し、領域ごとに別のオーバーレイとして表示する。
// VRでは px で固定する (デスクトップのUI倍率 UiSizeController は使わない。
// 大きさはVR内で掴んで拡大縮小できる)。
const Region = ({ layout, name, children }) => {
    const [x, y, w, h] = layout.regions[name];
    return (
        <div className={styles.region} data-vr-region={name} style={{ left: x, top: y, width: w, height: h }}>
            {children}
        </div>
    );
};

export const VrApp = () => {
    const atlas = useRef(null);
    // 並びはログの大きさで変わる (Python が決めて知らせる。models/overlay/overlay.py computeVrLayout)
    const { currentVrPanelLayout } = useVr();
    const layout = currentVrPanelLayout.data;
    const [atlas_width, atlas_height] = layout.atlas;
    const [, , panel_width, panel_height] = layout.regions.panel;
    const { asyncStdoutToPython } = useStdoutToPython();
    // 新しい並びで描き終えたら Python に知らせる (それまで撮ったフレームは表示に使われない)。
    // 並びはログの大きさで決まるので、ログの大きさを送る (全体の大きさはログを縮めても変わらないことがある)。
    // 描画が画面に反映されるのを待つため、2フレーム後に送る
    useEffect(() => {
        let second = null;
        const first = requestAnimationFrame(() => {
            second = requestAnimationFrame(() => asyncStdoutToPython("/run/vr_panel_layout_rendered", [panel_width, panel_height]));
        });
        return () => {
            cancelAnimationFrame(first);
            if (second !== null) cancelAnimationFrame(second);
        };
    }, [panel_width, panel_height]);
    // 開いているウィンドウはこの画面の中だけで持つ (同期される atom に置くとメインの値で上書きされる)。
    // 表示・非表示の結果だけを Python に伝える。一時ウィンドウは同時に1つだけ
    // 起動時はランチャーだけを出す (ログは必要なときにランチャーから開く)
    const [windows, setWindows] = useState({ log: false, popup: null });
    useEffect(() => {
        asyncStdoutToPython("/run/vr_panel_windows", { log: windows.log, popup: windows.popup !== null });
    }, [windows.log, windows.popup]);

    // VR設定ウィンドウを開いている間は、デスクトップで設定画面を開いたのと同じ扱いにする
    // (メインがメイン機能を止め、閉じたら戻す。VrPanelSyncController)
    const is_settings_open = windows.popup === "settings";
    useEffect(() => {
        emit("vr-panel-config-page", is_settings_open);
    }, [is_settings_open]);
    // デスクトップ側で設定画面が閉じられたら、VR設定ウィンドウも閉じる
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const was_config_page_open = useRef(false);
    useEffect(() => {
        const is_open = currentIsOpenedConfigPage.data === true;
        if (was_config_page_open.current && !is_open) {
            setWindows(w => (w.popup === "settings" ? { ...w, popup: null } : w));
        }
        was_config_page_open.current = is_open;
    }, [currentIsOpenedConfigPage.data]);

    const toggleLog = () => setWindows(w => ({ ...w, log: !w.log }));
    const openLog = () => setWindows(w => ({ ...w, log: true }));
    const togglePopup = (name) => setWindows(w => ({ ...w, popup: w.popup === name ? null : name }));
    const closePopup = () => setWindows(w => ({ ...w, popup: null }));

    return (
        <div ref={atlas} className={styles.atlas} style={{ width: atlas_width, height: atlas_height }}>
            <VrStateReceiver />
            <VrPointerHover />
            <UiLanguageController />
            <FontFamilyController />

            <Region layout={layout} name="panel"><VrLogWindow onClose={toggleLog} /></Region>
            <Region layout={layout} name="launcher"><VrLauncher windows={windows} toggleLog={toggleLog} openLog={openLog} togglePopup={togglePopup} /></Region>
            <Region layout={layout} name="popup"><VrPopupWindow popup={windows.popup} onClose={closePopup} /></Region>
            <Region layout={layout} name="toolbar"><VrToolbar /></Region>
            <Region layout={layout} name="tooltip"><VrTooltip atlasRef={atlas} layout={layout} /></Region>
        </div>
    );
};

// WebView2 はOSの本物のカーソル位置でホバーを判定するため、VRのポインタでは :hover が付かない。
// Python から届くポインタ位置 (この画面の論理px) にある要素へ data-vr-hover を付けて代わりにする。
const HOVER_TARGET = "button, [data-vr-hoverable]";
const VrPointerHover = () => {
    useEffect(() => {
        let hovered = null;
        const unlisten = listen("vr-panel-pointer", ({ payload }) => {
            const element = payload ? document.elementFromPoint(payload.x, payload.y) : null;
            const target = element?.closest(HOVER_TARGET) ?? null;
            if (target === hovered) return;
            hovered?.removeAttribute("data-vr-hover");
            target?.setAttribute("data-vr-hover", "");
            hovered = target;
        });
        return () => { unlisten.then(f => f()); };
    }, []);
    return null;
};

// メインウィンドウから送られてくるatomの値を、このウィンドウのatomへそのまま反映する。
const VrStateReceiver = () => {
    useEffect(() => {
        const jotai = getDefaultStore();
        const unlisten = listen("vr-panel-state", ({ payload }) => {
            for (const [name, encoded] of Object.entries(payload)) {
                const value = decodeOrdered(encoded);
                const atom = dynamicStoreRegistry[`Atom_${name}`];
                if (atom) jotai.set(atom, previous => name === "VrPanelLayout" &&
                    keepNewestVrLayout(previous.data, value.data) === previous.data ? previous : value);
            }
        });
        // 受信の準備ができてから全状態を要求する (メインが先に起動していた場合)
        unlisten.then(() => emit("vr-panel-ready"));
        return () => { unlisten.then(f => f()); };
    }, []);
    return null;
};
