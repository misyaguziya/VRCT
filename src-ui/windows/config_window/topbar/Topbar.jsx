import styles from "./Topbar.module.scss";

import { TitleBox } from "./title_box/TitleBox";
import { SectionTitleBox } from "./section_title_box/SectionTitleBox";
import { CompactSwitchBox } from "./compact_switch_box/CompactSwitchBox";

export const Topbar = () => {
    return (
        <div className={styles.container}>
            <div className={styles.wrapper}>
                <TitleBox />
                <SectionTitleBox />
                <CompactSwitchBox />
            </div>
        </div>
    );
};