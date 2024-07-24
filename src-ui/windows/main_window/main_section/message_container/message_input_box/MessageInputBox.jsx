import { useState } from "react";
import styles from "./MessageInputBox.module.scss";
import SendMessageSvg from "@images/send_message.svg?react";
import { useMessage } from "@logics/useMessage";
import { store } from "@store";
import { scrollToBottom } from "@logics/scrollToBottom";


export const MessageInputBox = () => {
    const [inputValue, setInputValue] = useState("");
    const { sendMessage } = useMessage();

    const onSubmitFunction = (e) => {
        e.preventDefault();
        sendMessage(inputValue);

        setTimeout(() => {
            scrollToBottom(store.log_box_ref);
        }, 10);

    };

    const onChangeFunction = (e) => {
        setInputValue(e.currentTarget.value);
    };

    return (
        <div className={styles.container}>
            <div className={styles.message_box_wrapper}>
                <textarea
                    className={styles.message_box_input_area}
                    onChange={onChangeFunction}
                    placeholder="Input Textfield"
                />
            </div>
            <button
                className={styles.message_send_button}
                type="button"
                onClick={onSubmitFunction}
            >
                <SendMessageSvg className={styles.message_send_icon} />
            </button>
        </div>
    );
};
