import { useResizable } from "react-resizable-layout";
import { useRef, useEffect, useState, forwardRef } from "react";
import styles from "./MessageContainer.module.scss";
import { LogBox } from "./log_box/LogBox";
import { MessageLogSettingsContainer } from "./message_log_settings_container/MessageLogSettingsContainer";
import { MessageInputBox } from "./message_input_box/MessageInputBox";
import { useMessageInputBoxRatio } from "@logics_main";

export const MessageContainer = () => {
    const { currentMessageInputBoxRatio, asyncSetMessageInputBoxRatio } = useMessageInputBoxRatio();
    const [ui_message_box_ratio, setUiMessageBoxRatio] = useState(false);
    const [is_hovered, setIsHovered] = useState(false);

    const container_ref = useRef(null);
    const separator_ref = useRef(null);
    const log_box_ref = useRef(null);
    const message_input_box_wrapper_ref = useRef(null);

    const calculateMessageInputBoxRatio = (position) => {
        if (log_box_ref.current && message_input_box_wrapper_ref.current && separator_ref.current && container_ref.current) {
            const container_padding_bottom = parseFloat(
                window.getComputedStyle(container_ref.current).paddingBottom
            );
            const total_height =
                log_box_ref.current.offsetHeight +
                separator_ref.current.offsetHeight * 2 +
                message_input_box_wrapper_ref.current.offsetHeight;
            const adjusted_position = position - container_padding_bottom;
            const message_box_ratio = (adjusted_position / total_height) * 100;
            return message_box_ratio;
        }
        console.warn("References not ready for calculation");
        return 10; // Default initial height percentage
    };

    const asyncSaveRatio = (position) => {
        if (position > 0) {
            asyncSetMessageInputBoxRatio(calculateMessageInputBoxRatio(position));
        }
    };

    const { position, separatorProps } = useResizable({
        axis: "y",
        reverse: true,
    });

    useEffect(() => {
        if (position > 0) {
            setUiMessageBoxRatio(calculateMessageInputBoxRatio(position));
            const timeout = setTimeout(() => {
                asyncSaveRatio(position);
            }, 200);
            return () => clearTimeout(timeout);
        }
    }, [position]);

    useEffect(() => {
        setUiMessageBoxRatio(currentMessageInputBoxRatio.data);
    }, [currentMessageInputBoxRatio]);

    return (
        <div className={styles.container} ref={container_ref}>
            <div
                className={styles.log_box_resize_wrapper}
                ref={log_box_ref}
                onMouseOver={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
            >
                <LogBox />
                <MessageLogSettingsContainer to_visible_toggle_bar={is_hovered} />
            </div>
            <Separator {...separatorProps} ref={separator_ref} />
            <div
                className={styles.message_box_resize_wrapper}
                ref={message_input_box_wrapper_ref}
                style={{ height: `${ui_message_box_ratio}%` }}
            >
                <MessageInputBox />
            </div>
        </div>
    );
};

const Separator = forwardRef((props, ref) => (
    <div tabIndex={0} className={styles.separator} ref={ref} {...props}>
        <span className={styles.separator_line}></span>
    </div>
));
