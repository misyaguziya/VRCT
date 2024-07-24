import { useResizable } from "react-resizable-layout";

import styles from "./MessageContainer.module.scss";

import { LogBox } from "./log_box/LogBox";
import { MessageInputBox } from "./message_input_box/MessageInputBox";

export const MessageContainer = () => {
    const { position, separatorProps } = useResizable({
        axis: "y",
        reverse: true
    });

    return (
        <div className={styles.container}>
            <LogBox />
            <Separator
                dir={"horizontal"}
                {...separatorProps}
            />
            <div className={styles.message_box_resize_wrapper} style={ { height: `${(position / 10) - 1.5 }rem` } }>
                <MessageInputBox />
            </div>
        </div>
    );
};

const Separator = ({ ...props }) => {
    return (
        <div tabIndex={0} className={styles.separator} {...props}>
            <span className={styles.separator_line}></span>
        </div>
    );
};