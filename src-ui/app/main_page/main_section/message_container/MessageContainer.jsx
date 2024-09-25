import { useResizable } from "react-resizable-layout";
import { useRef, useEffect, useState } from "react";
import styles from "./MessageContainer.module.scss";
import { appWindow } from "@tauri-apps/api/window"; // Tauriのwindow APIをインポート
import { LogBox } from "./log_box/LogBox";
import { MessageInputBox } from "./message_input_box/MessageInputBox";
import { useMessageInputBoxRatio } from "@logics_main/useMessageInputBoxRatio";

export const MessageContainer = () => {
    const { currentMessageInputBoxRatio, setMessageInputBoxRatio } = useMessageInputBoxRatio();
    const [message_box_height_in_rem, setMessageBoxHeightInRem] = useState(10);

    const container_ref = useRef(null);
    const log_box_ref = useRef(null);
    const message_box_wrapper_ref = useRef(null);

    const calculateMessageBoxRatioAndHeight = () => {
        if (log_box_ref.current && message_box_wrapper_ref.current) {
            const container_height = container_ref.current.offsetHeight;
            const container_padding_bottom = parseFloat(window.getComputedStyle(container_ref.current).paddingBottom);
            const total_height = container_height - container_padding_bottom;

            const message_box_height = message_box_wrapper_ref.current.offsetHeight;
            const message_box_ratio = (message_box_height / total_height) * 100;

            setMessageInputBoxRatio(message_box_ratio);

            const height_in_rem = convertRatioToRem(message_box_ratio);
            setMessageBoxHeightInRem(height_in_rem);
        }
    };

    const { position, separatorProps } = useResizable({
        axis: "y",
        reverse: true,
        onResizeEnd: calculateMessageBoxRatioAndHeight,
    });

    useEffect(() => {
        setMessageBoxHeightInRem((position / 10) - 1.5);
    }, [position]);


    useEffect(() => {
        setMessageBoxHeightInRem(convertRatioToRem(currentMessageInputBoxRatio.data));
    }, [currentMessageInputBoxRatio.data]);

    const convertRatioToRem = (ratio) => {
        const container_height = container_ref.current.offsetHeight;
        const container_padding_bottom = parseFloat(window.getComputedStyle(container_ref.current).paddingBottom);
        const total_height = container_height - container_padding_bottom;

        return ((ratio / 100) * total_height / 10) | 0; // 10px = 1rem
    };


        // Tauriのwindow resizeイベントをリッスン
        useEffect(() => {
            let resizeTimeout;

            // イベントのリスナーを設定
            const unlisten = appWindow.onResized(() => {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => {
                    calculateMessageBoxRatioAndHeight(); // リサイズが終了した後に実行
                }, 200); // ドラッグが終了したと見なすまでの遅延（200ms程度）
            });

            return () => {
                unlisten.then((dispose) => dispose()); // イベントリスナーを解除
            };
        }, []);

    return (
        <div className={styles.container} ref={container_ref}>
            <div ref={log_box_ref} className={styles.log_box_resize_wrapper}>
                <LogBox />
            </div>
            <Separator {...separatorProps} onDragStart={calculateMessageBoxRatioAndHeight} />
            <div
                className={styles.message_box_resize_wrapper}
                ref={message_box_wrapper_ref}
                style={{ height: `${message_box_height_in_rem}rem` }}
            >
                <MessageInputBox />
            </div>
        </div>
    );
};

const Separator = ({ onDragStart, ...props }) => {
    return (
        <div tabIndex={0} className={styles.separator} {...props} onDragStart={onDragStart}>
            <span className={styles.separator_line}></span>
        </div>
    );
};
