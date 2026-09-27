import { useEffect, useRef } from "react";
import { emit, listen } from "@tauri-apps/api/event";
import { getDefaultStore } from "jotai";

import { dynamicStoreRegistry } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useIsOpenedConfigPage } from "@logics_common";

// VRパネル (vr_panel ウィンドウ) をこのウィンドウの完全なミラーにする。
// - 全atomの値をVRパネルへ一方向に同期する (機能が増えても個別の同期コードは不要)
// - VRパネルからのバックエンド送信を代わりに行う。設定画面を開いている間は
//   メイン機能を一時停止しているため (ConfigPageCloseTriggerController)、拒否する
const jotai = getDefaultStore();

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
            payload[name] = value;
        } catch {
            // DOM参照など、ウィンドウをまたいで送れない値は同期しない
        }
    }
    emit("vr-panel-state", payload);
};

export const VrPanelSyncController = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const isOpenedConfigPageRef = useRef(currentIsOpenedConfigPage.data);
    isOpenedConfigPageRef.current = currentIsOpenedConfigPage.data;

    useEffect(() => {
        const entries = atomEntries();
        const unsubscribes = entries.map(([name, atom]) =>
            jotai.sub(atom, () => emitState([[name, atom]]))
        );
        const unlistenReady = listen("vr-panel-ready", () => emitState(atomEntries()));
        const unlistenStdout = listen("vr-panel-stdout", ({ payload }) => {
            // ウィンドウの開閉は状態を変えないので、設定画面を開いている間も通す
            if (isOpenedConfigPageRef.current === true && payload.path !== "/run/vr_panel_windows") {
                // VRパネル側で pending にした表示を元に戻すため、状態を送り直す
                emitState(atomEntries());
                return;
            }
            asyncStdoutToPython(payload.path, payload.value);
        });
        // VRパネルが先に起動していた場合に備えて、こちらからも一度送る
        emitState(entries);

        return () => {
            unsubscribes.forEach(unsubscribe => unsubscribe());
            unlistenReady.then(f => f());
            unlistenStdout.then(f => f());
        };
    }, []);

    return null;
};
