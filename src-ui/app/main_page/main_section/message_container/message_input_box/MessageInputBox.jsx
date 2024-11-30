import { useState, useEffect } from "react";
import styles from "./MessageInputBox.module.scss";
import SendMessageSvg from "@images/send_message.svg?react";
import { useMessage } from "@logics_common";
import { useSendMessageButtonType, useEnableAutoClearMessageInputBox } from "@logics_configs";
import { store } from "@store";
import { scrollToBottom } from "@utils";

export const MessageInputBox = () => {
    const [message_history, setMessageHistory] = useState([]);
    const [history_index, setHistoryIndex] = useState(-1);
    const {
        sendMessage,
        currentMessageLogs,
        currentMessageInputValue,
        updateMessageInputValue,
    } = useMessage();

    const { currentEnableAutoClearMessageInputBox } = useEnableAutoClearMessageInputBox();
    const { currentSendMessageButtonType } = useSendMessageButtonType();

    useEffect(() => {
        if (currentMessageLogs.data) {
            const sentMessages = currentMessageLogs.data
                .filter(log => log.category === "sent")
                .map(log => log.messages.original);
            setMessageHistory(sentMessages);
        }
    }, [currentMessageLogs.data]);

    const onSubmitFunction = (e) => {
        e.preventDefault();

        if (!currentMessageInputValue.data.trim()) return updateMessageInputValue("");

        sendMessage(currentMessageInputValue.data);

        if (currentEnableAutoClearMessageInputBox.data) updateMessageInputValue("");

        setTimeout(() => {
            scrollToBottom(store.log_box_ref);
        }, 10);

        setHistoryIndex(-1);
    };

    const onChangeFunction = (e) => {
        updateMessageInputValue(e.currentTarget.value);
    };

    const onKeyDownFunction = (e) => {
        if (currentSendMessageButtonType.data === "show_and_disable_enter_key") return;

        if (e.keyCode === 13 && !e.shiftKey) {
            onSubmitFunction(e);
        }

        if (e.key === "ArrowUp" && e.shiftKey) {
            e.preventDefault();

            if (history_index + 1 < message_history.length) {
                const new_index = history_index + 1;
                setHistoryIndex(new_index);
                updateMessageInputValue(message_history[message_history.length - 1 - new_index]);
            }
        }

        if (e.key === "ArrowDown" && e.shiftKey) {
            e.preventDefault();

            if (history_index > -1) {
                const new_index = history_index - 1;
                setHistoryIndex(new_index);
                setInputValue(
                    new_index >= 0
                        ? message_history[message_history.length - 1 - new_index]
                        : ""
                );
            }
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.message_box_wrapper}>
                <textarea
                    className={styles.message_box_input_area}
                    onChange={onChangeFunction}
                    placeholder="Input Textfield"
                    value={currentMessageInputValue.data}
                    onKeyDown={onKeyDownFunction}
                />
            </div>
            {currentSendMessageButtonType.data !== "hide" && (
                <SendMessageButton onSubmitFunction={onSubmitFunction} />
            )}
        </div>
    );
};

const SendMessageButton = ({ onSubmitFunction }) => {
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