import top_img from "@images/supporters/patreon_1600x400px.png";
import fanbox_logo from "@images/supporters/fanbox_logo.png";
import kofi_logo from "@images/supporters/kofi_logo.png";
import patreon_logo from "@images/supporters/patreon_logo.png";
import styles from "./SupportUsContainer.module.scss";
import clsx from "clsx";

export const SupportUsContainer = () => {
    return (
        <div id="support_us_container" className={styles.support_us_container}>
            <img className={styles.top_img} src={top_img} />
            <div className={styles.support_buttons_wrapper}>
                <div className={styles.support_us_button_wrapper}>
                    <a className={styles.support_button} href="https://vrct-dev.fanbox.cc" target="_blank" rel="noreferrer">
                        <img
                            src={fanbox_logo}
                            className={clsx(styles.support_img, styles.fanbox_logo)}
                        />
                        <div className={styles.spiral_top}></div>
                        <div className={styles.spiral_bottom}></div>
                    </a>
                    <a className={styles.support_button} href="https://ko-fi.com/vrct_dev" target="_blank" rel="noreferrer">
                        <img
                            src={kofi_logo}
                            className={clsx(styles.support_img, styles.kofi_logo)}
                        />
                        <div className={styles.spiral_top}></div>
                        <div className={styles.spiral_bottom}></div>
                    </a>
                    <a className={styles.support_button} href="https://www.patreon.com/vrct_dev" target="_blank" rel="noreferrer">
                        <img
                            src={patreon_logo}
                            className={clsx(styles.support_img, styles.patreon_logo)}
                        />
                        <div className={styles.spiral_top}></div>
                        <div className={styles.spiral_bottom}></div>
                    </a>
                </div>
                <div className={styles.lines_container}>
                    <div className={styles.line_basic}></div>
                    <div className={styles.line_fuwa}></div>
                    <div className={styles.line_mochi}></div>
                    <div className={styles.line_mogu}></div>
                </div>
            </div>
        </div>
    );
};