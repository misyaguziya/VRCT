import { useState } from "react";
import styles from "./MessageInputBox.module.scss";
import SendMessageSvg from "@images/send_message.svg?react";
import { useMessage } from "@logics_common/useMessage";
import { store } from "@store";
import { scrollToBottom } from "@utils/scrollToBottom";
import { useSendMessageButtonType } from "@logics_configs/useSendMessageButtonType";
import { useEnableAutoClearMessageBox } from "@logics_configs/useEnableAutoClearMessageBox";

export const MessageInputBox = () => {
    const [inputValue, setInputValue] = useState("");
    const { sendMessage } = useMessage();

    const { currentEnableAutoClearMessageBox } = useEnableAutoClearMessageBox();
    const { currentSendMessageButtonType } = useSendMessageButtonType();

    const onSubmitFunction = (e) => {
        e.preventDefault();
        sendMessage(inputValue);

        if (currentEnableAutoClearMessageBox.data) setInputValue("");

        setTimeout(() => {
            scrollToBottom(store.log_box_ref);
        }, 10);

    };

    const onChangeFunction = (e) => {
        setInputValue(e.currentTarget.value);
    };

    const onKeyDownFunction = (e) => {
        if (currentSendMessageButtonType.data === "show_and_disable_enter_key") return;
        if (e.keyCode == 13 && e.shiftKey == false) {
            onSubmitFunction(e);
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.message_box_wrapper}>
                <textarea
                    className={styles.message_box_input_area}
                    onChange={onChangeFunction}
                    placeholder="Input Textfield"
                    value={inputValue}
                    onKeyDown={onKeyDownFunction}
                />
            </div>
            { currentSendMessageButtonType.data !== "hide" && <SendMessageButton onSubmitFunction={onSubmitFunction}/> }
        </div>
    );
};


const SendMessageButton = ({onSubmitFunction}) => {
    return (
        <button
            className={styles.message_send_button}
            type="button"
            onClick={onSubmitFunction}
        >
            <SendMessageSvg className={styles.message_send_icon} />
        </button>
    );
};