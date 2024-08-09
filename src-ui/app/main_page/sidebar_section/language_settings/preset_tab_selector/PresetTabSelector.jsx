import styles from "./PresetTabSelector.module.scss";

export const PresetTabSelector = () => {
    return (
        <div className={styles.container}>
            <Tab preset_number={1} />
            <Tab preset_number={2} />
            <Tab preset_number={3} />
        </div>
    );
};

import clsx from "clsx";

import { useSelectedPresetTabStatus } from "@store";

const Tab = (props) => {
    const { updateSelectedPresetTabStatus, currentSelectedPresetTabStatus } = useSelectedPresetTabStatus();
    const onclickFunction = () => {
        updateSelectedPresetTabStatus(props.preset_number);
    };

    const class_names = clsx(styles["tab_container"], {
        [styles["is_selected"]]: (currentSelectedPresetTabStatus === props.preset_number) ? true : false
    });

    return (
        <div className={class_names} onClick={onclickFunction}>
            <p className={styles.tab_number}>{props.preset_number}</p>
        </div>
    );
};