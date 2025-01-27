import styles from "./SupportersContainer.module.scss";
import { useState, useEffect } from "react";
import vrct_supporters_title from "@images/supporters/vrct_supporters_title.png";
import { SupportersWrapper } from "./supporters_wrapper/SupportersWrapper";
import { clsx } from "clsx";
const SHUFFLE_INTERVAL_TIME = 20000;

export const SupportersContainer = () => {
    return (
        <div className={styles.supporters_container}>
            <img className={styles.vrct_supporters_title} src={vrct_supporters_title} />
            <p className={styles.vrct_supporters_desc}>{`VRCT3.0のアップデートに向けて、めちゃ大変な開発を支えてくれた "Early Supporters" です。\nThey are the 'Early Supporters' who supported us through the incredibly challenging development toward the VRCT3.0 update.`}</p>
            <ProgressBar />
            <SupportersWrapper />
            <ProgressBar />
            <p className={styles.vrct_supporters_desc_end}>{`みなさんのおかげで、みしゃ社長は布団で寝ることを許され(in開発室) しいなは喜び庭駆け回っています！！！ふわもちもぐもぐです！ありがとうございます。これからもまだまだ進化するVRCTをどうかよろしくお願いします！\nThanks to everyone, Misha has been granted the privilege of sleeping in a proper bed (in the development room), and Shiina is so happy, running around the yard! Fuwa-mochi-mogu-mogu! Thank you so much! We hope you'll continue to support the ever-evolving VRCT!`}</p>
        </div>
    );
};

const ProgressBar = () => {
    const [is_active, setIsActive] = useState(false);

    useEffect(() => {
        setIsActive(true);
        const interval = setInterval(() => {
            setIsActive(false);
            setTimeout(() => setIsActive(true), 50);
        }, SHUFFLE_INTERVAL_TIME);

        return () => clearInterval(interval);
    }, []);

    return (
        <div
            className={clsx(styles.progress_bar, {
                [styles.progress_bar_active]: is_active,
            })}
        />
    );
};