// import clsx from "clsx";
import styles from "./WindowTitleBar.module.scss";
import XMarkSvg from "@images/cancel.svg?react";
import SquareSvg from "@images/square.svg?react";
import LineSvg from "@images/line.svg?react";
import VrctSvg from "@images/vrct.svg?react";

import { appWindow } from "@tauri-apps/api/window";

export const WindowTitleBar = () => {

    const minimize = () => {
        appWindow.minimize();
    };

    const maximize = async () => {
        const maximizeState = await appWindow.isMaximized();
        if (!maximizeState) {
            appWindow.maximize();
        } else {
            appWindow.unmaximize();
        }
    };

    const close = () => {
        appWindow.close();
    };

    return (
        <div className={styles.container}>
            <div className={styles.wrapper} data-tauri-drag-region>
                <div className={styles.title_wrapper}>
                    <VrctSvg className={styles.title_svg}/>
                </div>

                <div className={styles.window_control_wrapper}>
                    <div className={styles.minimize_button} onClick={minimize}>
                        <LineSvg className={styles.line_svg}/>
                    </div>
                    <div className={styles.maximize_button} onClick={maximize}>
                        <SquareSvg className={styles.square_svg}/>
                    </div>
                    <div className={styles.close_button} onClick={close}>
                        <XMarkSvg className={styles.x_mark_svg}/>
                    </div>
                </div>
            </div>
        </div>
    );
};