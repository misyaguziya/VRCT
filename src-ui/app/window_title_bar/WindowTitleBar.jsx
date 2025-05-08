// import clsx from "clsx";
import styles from "./WindowTitleBar.module.scss";
import XMarkSvg from "@images/cancel.svg?react";
import SquareSvg from "@images/square.svg?react";
import LineSvg from "@images/line.svg?react";
import VrctSvg from "@images/vrct.svg?react";

import { getCurrentWindow } from "@tauri-apps/api/window";

export const WindowTitleBar = () => {

    const asyncMinimize = async () => {
        const appWindow = await getCurrentWindow();
        appWindow.minimize();
    };

    const asyncMaximize = async () => {
        const appWindow = await getCurrentWindow();
        const maximizeState = await appWindow.isMaximized();
        if (!maximizeState) {
            appWindow.maximize();
        } else {
            appWindow.unmaximize();
        }
    };

    const asyncClose = async () => {
        const appWindow = await getCurrentWindow();
        appWindow.close();
    };

    return (
        <div className={styles.container}>
            <div className={styles.wrapper} data-tauri-drag-region>
                <div className={styles.title_wrapper}>
                    <VrctSvg className={styles.title_svg}/>
                </div>

                <div className={styles.window_control_wrapper}>
                    <div className={styles.minimize_button} onClick={asyncMinimize}>
                        <LineSvg className={styles.line_svg}/>
                    </div>
                    <div className={styles.maximize_button} onClick={asyncMaximize}>
                        <SquareSvg className={styles.square_svg}/>
                    </div>
                    <div className={styles.close_button} onClick={asyncClose}>
                        <XMarkSvg className={styles.x_mark_svg}/>
                    </div>
                </div>
            </div>
        </div>
    );
};