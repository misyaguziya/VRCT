import React, { useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import Tooltip, { tooltipClasses } from '@mui/material/Tooltip';
import styles from "./MessageSubMenuContainer.module.scss";
import SendMessageSvg from "@images/send_message.svg?react";
import RefreshSvg from "@images/refresh_2.svg?react";

export const MessageSubMenuContainer = (props) => {
    const [is_holding, setIsHolding] = useState(false);
    const progressRef = useRef(null);
    const holdTimeout = useRef(null);

    const startHold = () => {
        setIsHolding(true);
        if (progressRef.current) {
        progressRef.current.style.transition = "width 500ms linear";
        progressRef.current.style.width = "100%";
        }
        holdTimeout.current = setTimeout(() => {
            props.resendFunction();
            props.setIsHovered(false);
        }, 500);
    };

    const cancelHold = () => {
        setIsHolding(false);
        if (progressRef.current) {
            progressRef.current.style.transition = "none";
            progressRef.current.style.width = "0%";
        }
        clearTimeout(holdTimeout.current);
    };

    const onClickFunction = () => {
        props.editFunction();

    };

    const offset = {
        popper: {
            sx: {
                [`&.${tooltipClasses.popper}[data-popper-placement*="top"] .${tooltipClasses.tooltip}`]: { marginBottom: "0.2em" },
            }
        }
    };

    return (
        <div className={styles.container}>
            <Tooltip
                title={<Title_p />}
                placement="top"
                slotProps={offset}
            >
                <button
                className={styles.resend_button}
                onMouseDown={startHold}
                onMouseUp={cancelHold}
                onMouseLeave={cancelHold}
                onClick={onClickFunction}
                >
                    <SendMessageSvg className={styles.send_message_svg} />
                    <RefreshSvg className={styles.refresh_svg} />
                    <div ref={progressRef} className={styles.hold_progress_bar}></div>
                </button>
            </Tooltip>
        </div>
    );
};

const Title_p = () => {
    const { t } = useTranslation();
    return <p className={styles.tooltip_title}>{t("main_page.message_log.resend_button_on_hover_desc")}</p>;
};
