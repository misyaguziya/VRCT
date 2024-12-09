import { clsx } from "clsx";
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

    return (
        <div>
            <Snackbar
                open={currentNotificationStatus.data.is_open}
                onClose={handleClose}
                TransitionComponent={SlideTransition}
                key={currentNotificationStatus.data.key}
                autoHideDuration={5000}
            >
                <div className={snackbar_classname}>
                    <p className={styles.snackbar_message}>{currentNotificationStatus.data.message}</p>
                </div>
            </Snackbar>
        </div>
    );
};

const SlideTransition = (props) => {
    return <Slide {...props} direction="up" />;
};
