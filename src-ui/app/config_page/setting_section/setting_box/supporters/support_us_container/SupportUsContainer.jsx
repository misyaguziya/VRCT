import fanbox_img from "@images/supporters/c_fanbox_1620x580.png";
import fanbox_button from "@images/supporters/fanbox_button.png";
import kofi_preparing from "@images/supporters/kofi_preparing.png";
import styles from "./SupportUsContainer.module.scss";

export const SupportUsContainer = () => {
    return (
        <div id="ttt" className={styles.support_us_container}>
            <img className={styles.fanbox_img} src={fanbox_img} />
            <div className={styles.support_us_button_wrapper}>
                <div className={styles.fanbox_wrapper}>
                    <a className={styles.fanbox_button} href="https://vrct-dev.fanbox.cc/" target="_blank" rel="noreferrer">
                        <img style={{ height: "100%", width: "100%", objectFit: "contain" }} src={fanbox_button} />
                    </a>
                    <p className={styles.mainly_japanese}>日本語 / Mainly Japanese</p>
                </div>
                <div className={styles.kofi_wrapper}>
                    <img className={styles.kofi_preparing} src={kofi_preparing} />
                    <p className={styles.mainly_english}>Mainly English</p>
                </div>
            </div>
        </div>
    );
};