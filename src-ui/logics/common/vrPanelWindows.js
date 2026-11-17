// VR 画面の開いている窓をメインが覚えておき、作り直した VR 画面 (SteamVR の再起動・VR UI の OFF → ON) で
// 開き直すための決まり。覚えるのはログ窓とキーボードだけ (言語・設定の一時ウィンドウは戻さない。設定を戻すと
// メイン機能が止まる)。VRCT を起動し直したときは何も覚えていない (ランチャーだけで始まる)。

export const VR_WINDOWS_PATH = "/run/vr_panel_windows";

// VR 画面の窓を持つか: VR UI が ON で、SteamVR に一度つながったら作り、VR UI を OFF にするまで残す
// (SteamVR が切れても作り直さない。作り直すと、作った直後の撮影の失敗に毎回入る)。
// ponytail: 窓を撮る作りの間の折衷。サイドカーをやめる移行で、MSKB と同じ窓なしの描画 (composition) にする
export const vrPanelWindowWanted = (had_window, enabled, steamvr) => enabled && (steamvr || had_window);

// VR 画面がバックエンドへ送った窓の状態から、覚える分
export const rememberedVrWindows = (value) => ({ log: value?.log === true, keyboard: value?.keyboard === true });

// 作り直した VR 画面: 覚えていた窓を開く (もう開いている窓は閉じない)
export const restoreVrWindows = (windows, remembered) => ({
    ...windows, log: windows.log || remembered.log, keyboard: windows.keyboard || remembered.keyboard,
});

// 何も開いていない最初の状態。これは送らない (メインが覚えている状態 = バックエンドが知っている状態を、
// 開き直す前に「全部閉じた」で上書きしない)
export const isUntouchedVrWindows = (windows) => !windows.log && windows.popup === null && !windows.keyboard;

// VR 画面の窓が無くなったとき (SteamVR の終了・VR UI の OFF): VR の設定ウィンドウが開いた設定画面は閉じる
// (「閉じた」はもう届かない。デスクトップが先に開いていた設定画面は閉じない)
export const configPageAfterVrPanelGone = (is_opened_by_vr) => (is_opened_by_vr ? false : null);
