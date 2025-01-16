import { appWindow } from "@tauri-apps/api/window";
import { register, unregisterAll, isRegistered } from "@tauri-apps/api/globalShortcut";
import { useEffect } from "react";
import { store } from "@store";
import { useHotkeys } from "@logics_configs";
import { useMainFunction } from "@logics_main";

// 修飾キーのパースを行う関数
const parseHotkey = (hotkeyString) => {
    const keyMap = {
        Ctrl: "Control",
        Alt: "Alt",
        Shift: "Shift",
        Meta: "Super",
    };

    // 入力文字列を分解して対応するキーを再結合
    return hotkeyString
        .map((key) => keyMap[key] || key) // 修飾キーをマップし、その他はそのまま
        .join("+");
};

export const GlobalHotKeyController = () => {
    const { currentHotkeys } = useHotkeys();

    const {
        toggleTranslation,
        toggleTranscriptionSend,
        toggleTranscriptionReceive,
    } = useMainFunction();

    useEffect(() => {
        const registerShortcuts = async () => {
            try {
                // 既存のショートカットをすべて解除
                await unregisterAll();

                const hotkeyEntries = Object.entries(currentHotkeys.data);

                for (const [actionKey, hotkeyRaw] of hotkeyEntries) {
                    if (!hotkeyRaw) continue;

                    const shortcut = parseHotkey(hotkeyRaw);
                    const isAlreadyRegistered = await isRegistered(shortcut);

                    if (!isAlreadyRegistered) {
                        await register(shortcut, async () => {
                            console.log(`Shortcut for "${actionKey}" triggered.`);

                            switch (actionKey) {
                                case "toggle_vrct_visibility": {
                                    const minimized = await appWindow.isMinimized();
                                    if (minimized) {
                                        appWindow.unminimize();
                                        await appWindow.setFocus();
                                        store.text_area_ref.current?.focus();
                                    } else {
                                        appWindow.minimize();
                                    }
                                    break;
                                }
                                case "toggle_translation": {
                                    toggleTranslation();
                                    break;
                                }
                                case "toggle_transcription_send": {
                                    toggleTranscriptionSend();
                                    break;
                                }
                                case "toggle_transcription_receive": {
                                    toggleTranscriptionReceive();
                                    break;
                                }
                                default: {
                                    console.warn(`No handler defined for action: ${actionKey}`);
                                    break;
                                }
                            }
                        });
                        console.log(`Registered global shortcut: ${shortcut} for action: ${actionKey}`);
                    }
                }
            } catch (error) {
                console.error("Failed to register global shortcuts:", error);
            }
        };

        registerShortcuts();

        // クリーンアップ関数でショートカットを解除
        return () => {
            unregisterAll().catch((error) => {
                console.error("Failed to unregister shortcuts:", error);
            });
        };
    }, [currentHotkeys.data]); // 監視対象を全体に変更

    return null;
};
