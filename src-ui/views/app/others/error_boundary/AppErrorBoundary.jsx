import { useState } from "react";
import { ErrorBoundary } from "react-error-boundary";
import XMarkSvg from "@images/cancel.svg?react";
import CopySvg from "@images/copy.svg?react";
import CheckMarkSvg from "@images/check_mark.svg?react";

import { ContactsContainer } from "./contacts_container/ContactsContainer";

import { useWindow } from "@logics_common";

import styles from "./AppErrorBoundary.module.scss";

export const AppErrorBoundary = ({children}) => {
    return (
        <ErrorBoundary
            fallbackRender={({ error }) => (
                <ErrorContainer error={error} />
            )
        }>
            {children}
        </ErrorBoundary>
    );
};

const ErrorContainer = ({error}) => {
    const [is_copied, setIsCopied] = useState(false);

    const formatted_stack = error ? formatStackTrace(error.stack) : "Unknown error";

    const copyToClipboard = async () => {
        if (is_copied) return;

        await navigator.clipboard.writeText(formatted_stack);
        setIsCopied(true);

        setTimeout(() => {
            setIsCopied(false);
        }, 1000);
    };

    return (
        <div className={styles.container}>
            <CloseButtonContainer />
            <div className={styles.wrapper}>
                <p className={styles.error_message}>An error occurred. Please restart VRCT or contact the developers.</p>
                {error ?
                    <div className={styles.error_detail_container}>
                        <div className={styles.error_stack_container}>
                            <p className={styles.error_stack}>
                                {formatted_stack}
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

// Duplicated
const CloseButtonContainer = () => {
    const { asyncCloseApp } = useWindow();
    return (
        <button className={styles.close_button_wrapper} onClick={asyncCloseApp}>
            <div className={styles.close_button}>
                <XMarkSvg className={styles.x_mark_svg}/>
            </div>
        </button>
    );
};


const formatStackTrace = (stack) => {
    if (!stack) return "";
    // フルパスの除去（例として window.location.origin や絶対パス部分を削除）
    // ※必要に応じて正規表現を調整してください
    const formatted = stack.replace(new RegExp(window.location.origin, "g"), "");

    return formatted;
};