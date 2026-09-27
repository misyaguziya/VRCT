import { emit } from "@tauri-apps/api/event";

// バックエンドから届く VR UI 上のポインタ位置 ({x, y} または null) を VR ウィンドウへ転送する。
// VR ウィンドウはバックエンドと直接つながっていないため、メインウィンドウが中継する。
export const useVrPanelPointer = () => {
    const forwardVrPanelPointer = (payload) => {
        emit("vr-panel-pointer", payload ?? null);
    };
    return { forwardVrPanelPointer };
};
