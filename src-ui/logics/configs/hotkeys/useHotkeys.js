import { appWindow } from "@tauri-apps/api/window";

import { store, useStore_Hotkeys } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";
import { useNotificationStatus } from "@logics_common";
import { useMainFunction } from "@logics_main";
import { register, unregisterAll, isRegistered } from "@tauri-apps/api/globalShortcut";

export const useHotkeys = () => {
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
    const { showNotification_Success, showNotification_Error, closeNotification } = useNotificationStatus();

    const setHotkeys = (hotkeys) => {
        pendingHotkeys();

        const updatedHotkeys = { ...currentHotkeys.data, ...hotkeys };
        const usedShortcuts = new Set();
        const conflictingKeys = [];

        for (const [actionKey, hotkey] of Object.entries(updatedHotkeys)) {
            if (!hotkey) continue;

            const shortcut = parseHotkey(hotkey);
            if (usedShortcuts.has(shortcut)) {
                showNotification_Error(`The hotkey ${shortcut} is already in use.`);
                updatedHotkeys[actionKey] = null;
                conflictingKeys.push(actionKey);
            } else {
                usedShortcuts.add(shortcut);
            }
        }

        updateHotkeys(updatedHotkeys);

        if (conflictingKeys.length === 0) {
            asyncStdoutToPython("/set/data/hotkeys", updatedHotkeys);
            closeNotification();
            return true;
        } else {
            return false;
        }
    };

    const registerShortcuts = async () => {
        try {
            await unregisterAll();

            const hotkeyEntries = Object.entries(currentHotkeys.data);

            for (const [actionKey, hotkeyRaw] of hotkeyEntries) {
                if (!hotkeyRaw) continue;

                const shortcut = parseHotkey(hotkeyRaw);
                const isAlreadyRegistered = await isRegistered(shortcut);

                if (!isAlreadyRegistered) {
                    await register(shortcut, async () => {
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

                }
            }
        } catch (error) {
            console.error("Failed to register global shortcuts:", error);
        }
    };

    return {
        currentHotkeys,
        getHotkeys,
        updateHotkeys,
        setHotkeys,
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