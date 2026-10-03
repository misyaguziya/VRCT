import { emit } from "@tauri-apps/api/event";
import { useStore_VrPanelLogOutOfView, useStore_VrPanelLauncherIntro } from "@store";

// バックエンドから届く VR UI 上のポインタ位置 ({x, y} または null) を VR ウィンドウへ転送する。
// VR ウィンドウはバックエンドと直接つながっていないため、メインウィンドウが中継する。
export const useVrPanelPointer = () => {
    const forwardVrPanelPointer = (payload) => {
        emit("vr-panel-pointer", payload ?? null);
    };
    return { forwardVrPanelPointer };
};

// ログウィンドウが視線から外れているか (バックエンドが変わったときだけ送る)。atom なので VR ウィンドウへも同期される
export const useVrPanelLogOutOfView = () => {
    const { currentVrPanelLogOutOfView, updateVrPanelLogOutOfView } = useStore_VrPanelLogOutOfView();
    return { currentVrPanelLogOutOfView, updateVrPanelLogOutOfView };
};

// ランチャーの起動演出の状態 ("idle" / "pending" / "playing")。バックエンドが変わったときだけ送る
export const useVrPanelLauncherIntro = () => {
    const { currentVrPanelLauncherIntro, updateVrPanelLauncherIntro } = useStore_VrPanelLauncherIntro();
    return { currentVrPanelLauncherIntro, updateVrPanelLauncherIntro };
};
