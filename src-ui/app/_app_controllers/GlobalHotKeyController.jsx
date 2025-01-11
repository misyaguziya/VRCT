import { appWindow } from "@tauri-apps/api/window";
import { register, unregisterAll, isRegistered } from "@tauri-apps/api/globalShortcut";
import { useEffect } from "react";
import { store } from "@store";
import { useHotkeys } from "@logics_configs";

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

    useEffect(() => {
        const registerShortcuts = async () => {
            const shortcut_raw = currentHotkeys.data.toggle_active_vrct;
            console.log(shortcut_raw);


            if (!shortcut_raw) {
                console.warn("No hotkey defined.");
                return;
            }

            // 入力文字列をTauriで使える形式に変換
            const shortcut = parseHotkey(shortcut_raw);
            // const shortcut = "F9";

            try {
                // 既存のショートカットをすべて解除
                await unregisterAll();

                // 新しいショートカットを登録
                const isAlreadyRegistered = await isRegistered(shortcut);
                if (!isAlreadyRegistered) {
                    await register(shortcut, async () => {
                        console.log(`Shortcut "${shortcut}" triggered, setting focus.`);
                        // const minimized = await appWindow.isMinimized();
                        // if (minimized === true) {
                        //     appWindow.unminimize();
                        //     await appWindow.setFocus();
                        //     store.text_area_ref.current?.focus();
                        // } else {
                        //     appWindow.minimize();
                        // }
                    });
                    console.log(`Registered global shortcut: ${shortcut}`);
                }
            } catch (error) {
                console.error("Failed to register global shortcut:", error);
            }
        };

        registerShortcuts();

        // クリーンアップ関数でショートカットを解除
        return () => {
            unregisterAll().catch((error) => {
                console.error("Failed to unregister shortcuts:", error);
            });
        };
    }, [currentHotkeys.data.toggle_active_vrct]); // 監視対象を明確に指定

    return null;
};
