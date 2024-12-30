import { useState, useEffect } from "react";
import styles from "./SplashComponent.module.scss";
import { StartUpProgressContainer } from "./start_up_progress_container/StartUpProgressContainer/";
import { DownloadModelsContainer } from "./download_models_container/DownloadModelsContainer/";
import MegaphoneSvg from "@images/megaphone.svg?react";
import XMarkSvg from "@images/cancel.svg?react";
import { appWindow } from "@tauri-apps/api/window";

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

const AnnouncementsContainer = () => {
    const labels = ["VRCT Real-Time Announcements", "VRCTからのお知らせ"];
    const [currentLabelIndex, setCurrentLabelIndex] = useState(0);


    useEffect(() => {
        const labelInterval = setInterval(() => {
            setCurrentLabelIndex((prevIndex) => (prevIndex + 1) % labels.length);
        }, 6000);
        return () => clearInterval(labelInterval);
    }, [labels.length]);

    return (
        <a
            href="https://docs.google.com/spreadsheets/d/1_L5i-1U6PB1dnaPPTE_5uKMfqOpkLziPyRkiMLi4mqU/edit?usp=sharing"
            target="_blank"
            rel="noreferrer"
        >
            <button className={styles.announcements_button}>
                <MegaphoneSvg className={styles.announcements_link_svg} />
                <p className={styles.announcements_label}>{labels[currentLabelIndex]}</p>
            </button>
        </a>
    );
};


const CloseButtonContainer = () => {
    const close = () => {
        appWindow.close();
    };

    return (
        <button className={styles.close_button_wrapper} onClick={close}>
            <div className={styles.close_button}>
                <XMarkSvg className={styles.x_mark_svg}/>
            </div>
        </button>
    );
};