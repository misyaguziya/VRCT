import React, { useRef, useLayoutEffect, useEffect } from "react";
import styles from "./LogBox.module.scss";
import { MessageContainer } from "./message_container/MessageContainer";
import { useMessage } from "@logics_common";
import { useMessageLogScroll } from "@logics_main";
import { store } from "@store";

export const LogBox = () => {
    const { currentMessageLogs } = useMessage();
    const { scrollToBottom, isScrolling } = useMessageLogScroll();
    const logContainerRef = useRef(null);

    useLayoutEffect(() => {
        store.log_box_ref = logContainerRef;
        if (!isScrolling) {
            scrollToBottom();
        }
    }, [currentMessageLogs.data, isScrolling]);

    return (
        <div id="log_container" className={styles.container} ref={logContainerRef}>
            <MessageLogUiSizeController />
            {currentMessageLogs.data.map((message_data) => (
                <MessageContainer key={message_data.id} {...message_data} />
            ))}
        </div>
    );
};

import { useMessageLogUiScaling } from "@logics_configs";
const MessageLogUiSizeController = () => {
    const { currentMessageLogUiScaling } = useMessageLogUiScaling();
    const font_size = currentMessageLogUiScaling.data / 100;

    useEffect(() => {
        const log_container_el = document.getElementById("log_container");
        log_container_el.style.setProperty("font-size", `${font_size}rem`);
    }, [currentMessageLogUiScaling.data]);

    return null;
};