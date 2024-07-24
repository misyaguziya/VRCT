import { useTranslation } from "react-i18next";
import clsx from "clsx";
import styles from "./MessageContainer.module.scss";

export const MessageContainer = ({ messages, status, category, created_at }) => {
    const { t } = useTranslation();

    const is_translated_exist = messages.translated.length >= 1;
    const is_pending = status === "pending";
    const is_sent_message = category === "sent";
    const category_text = is_sent_message ? t("main_window.textbox_tab_sent") : t("main_window.textbox_tab_received");

    const message_type_class_name = clsx({
        [styles.sent_message]: is_sent_message,
        [styles.received_message]: !is_sent_message,
    });

    return (
        <div className={clsx(styles.container, message_type_class_name)}>
            <div className={clsx(styles.info_box, message_type_class_name)}>
                <p className={styles.time}>{created_at}</p>
                <p className={clsx(styles.category, message_type_class_name)}>{category_text}</p>
                {is_sent_message && is_pending && <span className={styles.loader}></span>}
            </div>
            <div className={clsx(styles.message_box, message_type_class_name)}>
                {is_translated_exist
                    ? <WithTranslatedMessages messages={messages} />
                    : <p className={styles.message_main}>{messages.original}</p>
                }
            </div>
        </div>
    );
};

const WithTranslatedMessages = ({ messages }) => {
    return (
        <>
            <p className={styles.message_second}>{messages.original}</p>
            {messages.translated.map((message, index) => (
                <p key={index} className={styles.message_main}>{message}</p>
            ))}
        </>
    );
};
