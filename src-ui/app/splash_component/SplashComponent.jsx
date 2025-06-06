import { useState, useEffect } from "react";
import styles from "./SplashComponent.module.scss";
import { StartUpProgressContainer } from "./start_up_progress_container/StartUpProgressContainer/";
import { DownloadModelsContainer } from "./download_models_container/DownloadModelsContainer/";
import MegaphoneSvg from "@images/megaphone.svg?react";
import XMarkSvg from "@images/cancel.svg?react";
import { useWindow } from "@logics_common";
import clsx from "clsx";

export const SplashComponent = () => {
    return (
        <div className={styles.container}>
            <StartUpProgressContainer />
            <DownloadModelsContainer />
            <AnnouncementsContainer />
            <CloseButtonContainer />
        </div>
    );
};

const SHOW_MEGAPHONE_TIME = 500;

const AnnouncementsContainer = () => {
    const labels = ["Check the Latest Status", "最新の状況を確認"];
    const [is_shown, setIsShown] = useState(0);
    const [currentLabelIndex, setCurrentLabelIndex] = useState(0);
    const [is_labels_active, setIsLabelsActive] = useState(false);

    useEffect(() => {
        const showTimeout = setTimeout(() => {
            setIsShown(true);
        }, SHOW_MEGAPHONE_TIME);

        const labelsTimeout = setTimeout(() => {
            setIsLabelsActive(true);
        }, SHOW_MEGAPHONE_TIME + 15000);

        let labelInterval;
        if (is_labels_active) {
            labelInterval = setInterval(() => {
                setCurrentLabelIndex((prevIndex) => (prevIndex + 1) % labels.length);
            }, 4000);
        }

        return () => {
            clearTimeout(showTimeout);
            clearTimeout(labelsTimeout);
            if (labelInterval) clearInterval(labelInterval);
        };
    }, [is_labels_active, labels.length]);


    return (
        <a
            className={clsx(styles.announcements_button_wrapper, {
                [styles.is_shown]: is_shown,
                [styles.is_labels_active]: is_labels_active,
            })}
            href="https://docs.google.com/spreadsheets/d/1_L5i-1U6PB1dnaPPTE_5uKMfqOpkLziPyRkiMLi4mqU/edit?usp=sharing"
            target="_blank"
            rel="noreferrer"
        >
            <button className={styles.announcements_button}>
                <MegaphoneSvg className={styles.announcements_link_svg} />
                <p className={styles.announcements_label}>
                    {labels[currentLabelIndex]}
                </p>
            </button>
        </a>
    );
};


// Duplicated
const CloseButtonContainer = () => {
    const { asyncCloseApp } = useWindow();

    return (
        <button className={styles.close_button_wrapper} onClick={asyncCloseApp}>
            <div className={styles.close_button}>
                <XMarkSvg className={styles.x_mark_svg}/>
            </div>
        </button>
    );
};