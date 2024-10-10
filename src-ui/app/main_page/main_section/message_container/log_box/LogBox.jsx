import { useEffect, useLayoutEffect, useRef, useState } from "react";
import styles from "./LogBox.module.scss";
import { store } from "@store";
import { MessageContainer } from "./message_container/MessageContainer";
import { scrollToBottom } from "@utils/scrollToBottom";
import { useMessage } from "@logics_common";

export const LogBox = () => {
    const { currentMessageLogs } = useMessage();
    const log_container_ref = useRef(null);
    const [is_scrolling, setIsScrolling] = useState(false);


    useLayoutEffect(() => {
        store.log_box_ref = log_container_ref;
        if (!is_scrolling) {
            scrollToBottom(store.log_box_ref, true);
        }
    }, [currentMessageLogs.data]);

    useEffect(() => {
        const handleScroll = () => {
            const element = log_container_ref.current;
            const currentScrollTop = element.scrollTop;
            const at_bottom = element.scrollHeight - currentScrollTop === element.clientHeight;

            if (at_bottom) {
                setIsScrolling(false);
            } else {
                setIsScrolling(true);
            }
        };

        const element = log_container_ref.current;
        element.addEventListener("scroll", handleScroll);

        return () => {
            element.removeEventListener("scroll", handleScroll);
        };
    }, []);

    return (
        <div id="log_container" className={styles.container} ref={log_container_ref}>
            <MessageLogUiSizeController />
            {currentMessageLogs.data.map(message_data => (
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