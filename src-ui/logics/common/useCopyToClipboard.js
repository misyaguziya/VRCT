import { useEffect, useRef, useState } from "react";
import { useI18n } from "@useI18n";
import { useNotificationStatus } from "./useNotificationStatus";

export const useCopyToClipboard = ({
    duration = 1000,
    show_error_notification = true,
    onErrorFunction,
} = {}) => {
    const { t } = useI18n();
    const { showNotification_Error } = useNotificationStatus();

    const [is_copied, setIsCopied] = useState(false);
    const timer_ref = useRef(null);

    useEffect(() => () => clearTimeout(timer_ref.current), []);

    const copyToClipboard = async (text) => {
        if (is_copied) return;
        try {
            await navigator.clipboard.writeText(text);
            setIsCopied(true);
            timer_ref.current = setTimeout(() => setIsCopied(false), duration);
        } catch (error) {
            console.error("[useCopyToClipboard] copy failed", error);
            if (show_error_notification) {
                showNotification_Error(t("common_error.copy_to_clipboard_failed"));
            }
            onErrorFunction?.(error);
        }
    };

    return { is_copied, copyToClipboard };
};


