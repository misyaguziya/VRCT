import { useState } from "react";
import { useI18n } from "@useI18n";
import clsx from "clsx";
import styles from "./MessageContainer.module.scss";
import { MessageSubMenuContainer } from "./message_sub_menu_container/MessageSubMenuContainer";
import { useMessage } from "@logics_common";
import { useAppearance } from "@logics_configs";

export const MessageContainer = ({ messages, status, category, created_at }) => {
    const { t } = useI18n();
    const {
        sendMessage,
        updateMessageInputValue,
    } = useMessage();
    const { currentShowResendButton } = useAppearance();
    const [is_hovered, setIsHovered] = useState(false);
    const [is_locked, setIsLocked] = useState(false);

    const resendFunction = () => {
        sendMessage(messages.original.message);
    };
    const editFunction = () => {
        updateMessageInputValue(messages.original.message);
    };

    const handleMouseEnter = () => {
        if (!is_locked) {
            setIsHovered(true);
        }
    };

    const handleMouseLeave = () => {
        setIsHovered(false);
        setIsLocked(false);
    };

    const lockHoverState = () => {
        setIsHovered(false);
        setIsLocked(true);
    };

    const is_translation_exist = messages.translations?.length > 0;
    const is_pending = status === "pending";
    const is_sent_message = category === "sent";
    const is_system_message = category === "system";
    const category_text = is_sent_message
        ? t("main_page.message_log.sent")
        : is_system_message
        ? t("main_page.message_log.system")
        : t("main_page.message_log.received");

    const message_type_class_name = clsx({
        [styles.sent_message]: is_sent_message,
        [styles.received_message]: !is_sent_message && !is_system_message,
        [styles.system_message]: is_system_message,
    });

    return (
        <div
            className={clsx(styles.container, message_type_class_name)}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            <div className={clsx(styles.message_wrapper, message_type_class_name)}>
                <div className={clsx(styles.info_box, message_type_class_name)}>
                    <p className={styles.time}>{created_at}</p>
                    <p className={clsx(styles.category, message_type_class_name)}>{category_text}</p>
                    {is_sent_message && is_pending && <span className={styles.loader}></span>}
                </div>
                <div className={clsx(styles.message_box, message_type_class_name)}>
                    {is_system_message ? (
                        <p className={styles.message_main_system}>{messages.original.message}</p>
                    ) : is_translation_exist ? (
                        <WithTranslatedMessages messages={messages} />
                    ) : (
                        <OriginalMessage messages={messages} />
                    )}
                </div>
            </div>
            {currentShowResendButton.data && is_sent_message && is_hovered ? (
                <MessageSubMenuContainer
                    setIsHovered={lockHoverState}
                    resendFunction={resendFunction}
                    editFunction={editFunction}
                />
            ) : null}
        </div>
    );
};

const MessageWithTransliteration = ({ item }) => {
    const renderTokenNode = (token, key) => {
        const orig = token.orig ?? "";
        const hira = token.hira ?? "";
        const hepburn = token.hepburn ?? "";

        if (hira && hira === orig && hepburn) {
            return (
                <span key={key} title={hepburn} className={styles.with_hepburn}>
                    {orig}
                </span>
            );
        }

        if (hira && hira !== orig && hepburn) {
            return (
                <ruby key={key} title={hepburn} className={styles.with_hepburn}>
                    {orig}
                    <rt>{hira}</rt>
                </ruby>
            );
        }

        if (hepburn && hepburn !== orig) {
            return (
                <ruby key={key} className={styles.ruby}>
                    {orig}
                    <rt>{hepburn}</rt>
                </ruby>
            );
        }

        return (
            <span key={key} className={styles.original_only}>
                {orig}
            </span>
        );
    };

    if (!item.transliteration.length) {
        return <p className={styles.message_main}>{item.message}</p>;
    }

    return (
        <p className={styles.message_main}>
            {item.transliteration.map((token, idx) => renderTokenNode(token, idx))}
        </p>
    );
};

const OriginalMessage = ({ messages }) => {
    return (
        <>
            <MessageWithTransliteration item={messages.original} />
        </>
    );
};

const WithTranslatedMessages = ({ messages }) => {
    return (
        <>
            <p className={styles.message_second}>{messages.original.message}</p>
            {messages.translations.map((item, idx) => (
                <div key={idx}>
                    <MessageWithTransliteration item={item} />
                </div>
            ))}
        </>
    );
};
