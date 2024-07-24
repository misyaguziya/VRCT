import styles from "./PresetSelectTabs.module.scss";

export const PresetSelectTabs = () => {
    return (
        <div className={styles.container}>
            <Tab preset_number={1} />
            <Tab preset_number={2} />
            <Tab preset_number={3} />
        </div>
    );
};

import clsx from "clsx";

import { useSelectedTab } from "@store";

const Tab = (props) => {
    const { updateSelectedTab, currentSelectedTab } = useSelectedTab();
    const onclickFunction = () => {
        updateSelectedTab(props.preset_number);
    };

    const class_names = clsx(styles["tab_container"], {
        [styles["is_selected"]]: (currentSelectedTab === props.preset_number) ? true : false
    });

    return (
        <div className={class_names} onClick={onclickFunction}>
            <p className={styles.tab_number}>{props.preset_number}</p>
        </div>
    );
};