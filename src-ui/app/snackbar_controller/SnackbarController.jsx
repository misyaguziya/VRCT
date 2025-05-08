import clsx from "clsx";
import Snackbar from "@mui/material/Snackbar";
import Slide from "@mui/material/Slide";

import styles from "./SnackbarController.module.scss";
import { useNotificationStatus } from "@logics_common";

export const SnackbarController = () => {
    const { currentNotificationStatus, closeNotification } = useNotificationStatus();

    const handleClose = (event, reason) => {
        closeNotification(event, reason);
    };

    const snackbar_classname = clsx(styles.snackbar_content, {
        [styles.is_success]: currentNotificationStatus.data.status === "success",
        [styles.is_error]: currentNotificationStatus.data.status === "error",
    });

    const settings = currentNotificationStatus.data;

    let hide_duration = 5000;
    if (settings.options?.hide_duration === null) hide_duration = null;
    if (Number(settings.options?.hide_duration)) hide_duration = settings.options.hide_duration;

    return (
        <div>
            <Snackbar
                open={settings.is_open}
                onClose={handleClose}
                TransitionComponent={SlideTransition}
                key={settings.key}
                autoHideDuration={hide_duration}
            >
                <div className={snackbar_classname}>
                    <p className={styles.snackbar_message}>{settings.message}</p>
                </div>
            </Snackbar>
        </div>
    );
};

const SlideTransition = (props) => {
    return <Slide {...props} direction="up" />;
};
