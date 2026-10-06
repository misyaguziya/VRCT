import { store, useStore_Hotkeys } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { useNotificationStatus } from "@logics_common";
import { useMainFunction } from "@logics_main";
import { register, unregister, unregisterAll, isRegistered } from "@tauri-apps/plugin-global-shortcut";
import { useI18n } from "@useI18n";

export const useHotkeys = () => {
    const appWindow = store.appWindow;
    const { t } = useI18n();

    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentHotkeys, updateHotkeys, pendingHotkeys } = useStore_Hotkeys();
    const {
        toggleTranslation,
        toggleTranscriptionSend,
        toggleTranscriptionReceive,
    } = useMainFunction();

    const getHotkeys = () => {
        pendingHotkeys();
        asyncStdoutToPython("/get/data/hotkeys");
    };
    const { showNotification_SaveSuccess, showNotification_Error, closeNotification } = useNotificationStatus();

    const setHotkeys = async (hotkeys) => {
        const [targetActionKey, targetHotkey] = Object.entries(hotkeys)[0];

        // 削除の場合は競合チェックなしで保存
        if (!targetHotkey) {
            pendingHotkeys();
            const updatedHotkeys = { ...currentHotkeys.data, [targetActionKey]: null };
            updateHotkeys(updatedHotkeys);
            asyncStdoutToPython("/set/data/hotkeys", updatedHotkeys);
            closeNotification();
            return true;
        }

        const targetShortcut = parseHotkey(targetHotkey);
        const targetDisplay = targetHotkey.join(" + ");
        const actionLabel = getHotkeyActionLabel(targetActionKey, t);

        // 1. VRCT内の他のホットキーと重複していないかチェック
        for (const [actionKey, hotkey] of Object.entries(currentHotkeys.data)) {
            if (actionKey === targetActionKey || !hotkey) continue;
            const shortcut = parseHotkey(hotkey);
            if (shortcut === targetShortcut) {
                showNotification_Error(
                    t("config_page.hotkeys.error_in_use", {
                        action_name: actionLabel,
                        hotkey: targetDisplay,
                    })
                );
                return false;
            }
        }

        // 2. OS / 他のアプリケーションで既に使用されていないか（テスト登録）
        let isOsConflict = false;
        try {
            await register(targetShortcut, () => {});
            await unregister(targetShortcut);
        } catch (err) {
            console.warn(`Hotkey registration test failed for ${targetShortcut}:`, err);
            isOsConflict = true;
        }

        if (isOsConflict) {
            showNotification_Error(
                t("config_page.hotkeys.error_in_use", {
                    action_name: actionLabel,
                    hotkey: targetDisplay,
                })
            );
            return false;
        }

        // 3. 競合なし：保存してバックエンドに送信
        pendingHotkeys();
        const updatedHotkeys = { ...currentHotkeys.data, [targetActionKey]: targetHotkey };
        updateHotkeys(updatedHotkeys);
        asyncStdoutToPython("/set/data/hotkeys", updatedHotkeys);
        closeNotification();
        return true;
    };

    const registerShortcuts = async () => {
        try {
            await unregisterAll();

            const hotkeyEntries = Object.entries(currentHotkeys.data);
            const failedHotkeys = [];

            for (const [actionKey, hotkeyRaw] of hotkeyEntries) {
                if (!hotkeyRaw) continue;

                const shortcut = parseHotkey(hotkeyRaw);
                try {
                    await register(shortcut, async (event) => {
                        if (event.state !== "Pressed") return;
                        switch (actionKey) {
                            case "toggle_vrct_visibility": {
                                const minimized = await appWindow.isMinimized();
                                if (minimized) {
                                    await appWindow.unminimize();
                                    await appWindow.setFocus();
                                    store.text_area_ref.current?.focus();
                                } else {
                                    await appWindow.minimize();
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
                } catch (error) {
                    console.warn(`Failed to register global shortcut ${shortcut} for ${actionKey}:`, error);
                    failedHotkeys.push({
                        actionKey,
                        hotkey: hotkeyRaw.join(" + "),
                    });
                }
            }

            if (failedHotkeys.length > 0) {
                // 起動時 / 有効化時に他アプリで使用されていて登録できなかったホットキーを通知（設定は削除しない）
                failedHotkeys.forEach(({ actionKey, hotkey }) => {
                    const actionLabel = getHotkeyActionLabel(actionKey, t);
                    showNotification_Error(
                        t("config_page.hotkeys.error_failed_to_register_at_launch", {
                            action_name: actionLabel,
                            hotkey,
                        }),
                        { hide_duration: 8000 }
                    );
                });
            }
        } catch (error) {
            console.error("Failed to register global shortcuts:", error);
        }
    };

    const setSuccessHotkeys = (hotkeys) => {
        updateHotkeys(hotkeys);
        showNotification_SaveSuccess();
    };

    return {
        currentHotkeys,
        getHotkeys,
        updateHotkeys,
        setHotkeys,
        setSuccessHotkeys,
        registerShortcuts,
        unregisterAll,
    };
};

// 修飾キーのパースを行う関数
const parseHotkey = (hotkeyString) => {
    const keyMap = {
        Ctrl: "Control",
        Alt: "Alt",
        Shift: "Shift",
        Meta: "Super",
    };


    return hotkeyString
        .map((key) => keyMap[key] || key)
        .join("+");
};

// アクション名（多言語対応）を取得する関数
const getHotkeyActionLabel = (actionKey, t) => {
    switch (actionKey) {
        case "toggle_vrct_visibility":
            return t("config_page.hotkeys.toggle_vrct_visibility.label");
        case "toggle_translation":
            return t("config_page.hotkeys.toggle_translation.label", {
                translation: t("main_page.translation"),
            });
        case "toggle_transcription_send":
            return t("config_page.hotkeys.toggle_transcription_send.label", {
                transcription_send: t("main_page.transcription_send"),
            });
        case "toggle_transcription_receive":
            return t("config_page.hotkeys.toggle_transcription_receive.label", {
                transcription_receive: t("main_page.transcription_receive"),
            });
        default:
            return actionKey;
    }
};