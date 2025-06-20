import React, { useEffect, useState } from "react";
import { ToastContainer, toast, cssTransition } from "react-toastify";
import clsx from "clsx";

import "./ReactToastifyOverrideClass.scss";
import styles from "./SnackbarController.module.scss";

import XMarkSvg from "@images/cancel.svg?react";
import WarningSvg from "@images/warning.svg?react";
import MegaphoneSvg from "@images/megaphone.svg?react";
import CheckMarkSvg from "@images/check_mark.svg?react";
import ErrorSvg from "@images/error.svg?react";

import { useNotificationStatus } from "@logics_common";

const CustomTransition = cssTransition({
    enter: "fade_in",
    exit: "fade_out",
    collapse: false,
});


export const SnackbarController = () => {
    const { currentNotificationStatus, closeNotification } = useNotificationStatus();
    const [containerKey, setContainerKey] = useState(0);

    const settings = currentNotificationStatus.data;

    const snackbar_classname = clsx(
        styles.snackbar_content,
        {
            [styles.is_success]: settings.status === "success",
            [styles.is_warning]: settings.status === "warning",
            [styles.is_error]:   settings.status === "error",
        }
    );

    let hideDuration = 5000;
    if (settings.options?.hide_duration === null) {
        hideDuration = false;
    } else if (Number(settings.options?.hide_duration)) {
        hideDuration = Number(settings.options?.hide_duration);
    }

    const to_hide_progress_bar = (settings.options?.to_hide_progress_bar === true) ? true : false;

    useEffect(() => {
        if (!settings.is_open) return;

        const message_text = settings.message;
        const category_id = settings.category_id ? settings.category_id : message_text;

        setContainerKey(prevKey => prevKey + 1);

        setTimeout(() => {
            toast(message_text, {
                toastId: category_id,
                type: settings.status,
                autoClose: hideDuration,
                transition: CustomTransition,
                toastClassName: snackbar_classname,
                progressClassName: styles.toast_progress,
                closeButton: <CloseButtonContainer />,
                onClose: () => {
                    closeNotification();
                },
            });
        }, 50);
    }, [settings]);

    return (
        <ToastContainer
            key={containerKey}
            position="bottom-left"
            transition={CustomTransition}
            hideProgressBar={to_hide_progress_bar}
            newestOnTop={false}
            closeOnClick={false}
            pauseOnFocusLoss={false}
            draggable={false}
            pauseOnHover={true}
            theme="dark"
            icon={({ type }) => {
                switch (type) {
                    case "info":
                        return <MegaphoneSvg className={styles.megaphone_svg} />;
                    case "error":
                        return <ErrorSvg className={styles.error_svg} />;
                    case "success":
                        return <CheckMarkSvg className={styles.check_mark_svg} />;
                    case "warning":
                        return <WarningSvg className={styles.warning_svg} />;
                    default:
                        return null;
                }
            }}
        />
    );
};

const CloseButtonContainer = ({ closeToast }) => {
    return (
        <button className={styles.close_button_wrapper} onClick={closeToast}>
            <div className={styles.close_button}>
                <XMarkSvg className={styles.x_mark_svg} />
            </div>
        </button>
    );
};