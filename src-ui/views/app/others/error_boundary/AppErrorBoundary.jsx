import { useState } from "react";
import { ErrorBoundary } from "react-error-boundary";

import CopySvg from "@images/copy.svg?react";
import CheckMarkSvg from "@images/check_mark.svg?react";
import ExternalLinkSvg from "@images/external_link.svg?react";

import { ContactsContainer } from "./contacts_container/ContactsContainer";

import {
    useWindow,
    useUpdateSoftware,
    useIsSoftwareUpdating,
    useSoftwareVersion,
    useComputeMode,
} from "@logics_common";
import { CloseButton } from "@common_components";

import styles from "./AppErrorBoundary.module.scss";

const VRCT_STATUS_URL = "https://misyaguziya.github.io/VRCT-Docs/docs/faq/#vrct-status";

export const AppErrorBoundary = ({children}) => {
    const [errorInfo, setErrorInfo] = useState(null);

    return (
        <ErrorBoundary
            onError={(error, info) => setErrorInfo(info)}
            fallbackRender={({ error }) => (
                <ErrorContainer error={error} errorInfo={errorInfo} />
            )
        }>
            {children}
        </ErrorBoundary>
    );
};

const ErrorContainer = ({error, errorInfo}) => {
    const { asyncCloseApp } = useWindow();
    const { currentSoftwareVersion } = useSoftwareVersion();
    const [is_copied, setIsCopied] = useState(false);

    const formatted_stack = error ? formatStackTrace(error.stack) : "Unknown error";
    const app_version = currentSoftwareVersion?.data || "Unknown";

    const error_log_text = [
        `Version: ${app_version}`,
        `Date: ${new Date().toISOString().replace('T', ' ').split('.')[0]}`,
        "",
        "=== Error Stack ===",
        formatted_stack,
        "",
        "=== Component Stack ===",
        errorInfo?.componentStack ? formatStackTrace(errorInfo.componentStack) : "Not available",
    ].join("\n");

    const copyToClipboard = async () => {
        if (is_copied) return;

        await navigator.clipboard.writeText(error_log_text);
        setIsCopied(true);

        setTimeout(() => {
            setIsCopied(false);
        }, 1000);
    };

    return (
        <div className={styles.container}>
            <div className={styles.drag_able_area} data-tauri-drag-region></div>
            <CloseButton variant="active_error" onClick={asyncCloseApp} />
            <div className={styles.wrapper}>
                <p className={styles.error_message}>An error occurred. Please restart VRCT or contact the developers.</p>
                <SafeActionButtons />
                {error ?
                    <div className={styles.error_detail_container}>
                        <div className={styles.error_stack_container}>
                            <p className={styles.error_stack}>
                                {error_log_text}
                            </p>
                        </div>
                        <button className={styles.copy_error_message_button} onClick={copyToClipboard}>
                            <p className={styles.copy_text}>Copy</p>
                            {is_copied
                                ? <CheckMarkSvg className={styles.check_mark_svg}/>
                                : <CopySvg className={styles.copy_svg}/>
                            }
                        </button>
                    </div>
                : null}
                <ContactsContainer />
            </div>
        </div>
    );
};


const SafeActionButtons = () => {
    try {
        return <ActionButtons />;
    } catch {
        return null;
    }
};

const ActionButtons = () => {
    const { updateSoftware, updateSoftware_CUDA } = useUpdateSoftware();
    const { currentIsSoftwareUpdating, updateIsSoftwareUpdating } = useIsSoftwareUpdating();
    const { currentLatestSoftwareVersionInfo } = useSoftwareVersion();
    const { currentComputeMode } = useComputeMode();

    const is_update_available = currentLatestSoftwareVersionInfo?.data?.is_update_available === true;
    const is_updating = currentIsSoftwareUpdating?.data === true;
    const is_cpu = currentComputeMode?.data === "cpu";

    const onClickUpdate = () => {
        try {
            updateIsSoftwareUpdating(true);
            if (is_cpu) {
                updateSoftware();
            } else {
                updateSoftware_CUDA();
            }
        } catch (e) {
            console.error("[AppErrorBoundary] Update failed:", e);
        }
    };


    return (
        <div className={styles.action_buttons_container}>
            {is_update_available && (
                <button
                    className={styles.update_button}
                    onClick={onClickUpdate}
                    disabled={is_updating}
                >
                    {is_updating ? "Updating..." : "Update Available — Update Now"}
                </button>
            )}
            <a
                className={styles.status_link_button}
                href={VRCT_STATUS_URL}
                target="_blank"
                rel="noreferrer"
            >
                <span>Check VRCT Status</span>
                <ExternalLinkSvg className={styles.external_link_svg} />
            </a>
        </div>
    );
};

const formatStackTrace = (stack) => {
    if (!stack) return "";
    // フルパスの除去（例として window.location.origin や絶対パス部分を削除）
    const formatted = stack.replace(new RegExp(window.location.origin, "g"), "");

    return formatted;
};