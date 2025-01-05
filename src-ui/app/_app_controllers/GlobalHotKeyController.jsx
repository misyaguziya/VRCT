    import { appWindow } from "@tauri-apps/api/window";
    import { register, unregisterAll, isRegistered } from "@tauri-apps/api/globalShortcut";
    import { useEffect, useRef } from "react";
    import { store } from "@store";

    export const GlobalHotKeyController = () => {
        const is_initialized = useRef(false);
        useEffect(() => {
            if (is_initialized.current) return;

            const registerShortcuts = async () => {
                const shortcut = "Alt+Y";
                const is_already_registered = await isRegistered(shortcut);
                if (is_already_registered) return;

                await register(shortcut, async () => {
                    console.log("Shortcut triggered, setFocus");
                    appWindow.unminimize();
                    await appWindow.setFocus();
                    store.text_area_ref.current?.focus();
                });
            };

            registerShortcuts();
            is_initialized.current = true;

            return () => {
                unregisterAll().catch((error) => {
                    console.error("Failed to unregister shortcuts:", error);
                });
            };
        }, []);

        return null;
    };
