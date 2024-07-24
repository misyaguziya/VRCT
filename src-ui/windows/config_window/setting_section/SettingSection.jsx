import styles from "./SettingSection.module.scss";
import { SettingBox } from "./setting_box/SettingBox";

export const SettingSection = () => {
    return (
        <div className={styles.scroll_container}>
            <div className={styles.container}>
                <SettingBox />
            </div>
        </div>
    );
};