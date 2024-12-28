import { useState, useEffect } from "react";
import styles from "./Supporters.module.scss";
import clsx from "clsx";
import { useTranslation } from "react-i18next";

import {
    useSettingBoxScrollPosition,
} from "@logics_configs"

const supporter_images = import.meta.glob("@images/supporters/supporters_images/*.{png,jpg,jpeg,svg}", { eager: true });
const chato_expression_images = import.meta.glob("@images/supporters/chato_expressions/*.{png,jpg,jpeg,svg}", { eager: true });
import fanbox_img from "@images/supporters/c_fanbox_1620x580.png";
import vrct_supporters_title from "@images/supporters/vrct_supporters_title.png";
import fanbox_button from "@images/supporters/fanbox_button.png";
import kofi_preparing from "@images/supporters/kofi_preparing.png";

import ExternalLink from "@images/external_link.svg?react";

const mogu_count = 8;
const mochi_count = 3;
const fuwa_count = 4;
const basic_count = 5;
const former_count = 2;
const and_you_count = 1;
const default_icon_numbers = ["05", "06", "07", "11"];

const supporters_filenames = Array.from({ length: 23 }, (_, index) => `supporter_${String(index + 1).padStart(2, "0")}`);
const chato_expressions_filenames = Array.from({ length: 7 }, (_, index) => `chato_expression_${String(index + 1).padStart(2, "0")}`);

const SHUFFLE_INTERVAL_TIME = 20000;
const shuffleArray = (array) => {
    return array
        .map((value) => ({ value, sort: Math.random() }))
        .sort((a, b) => a.sort - b.sort)
        .map(({ value }) => value);
};

export const Supporters = () => {
    return (
        <div className={styles.container}>
            <SupportUsContainer />
            <SupportersContainer />
        </div>
    );
};

const SupportUsContainer = () => {
    return (
        <div className={styles.support_us_container}>
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

const getRandomImage = (images) => {
    const random_index = Math.floor(Math.random() * images.length);
    return images[random_index];
};

export const SupportersContainer = () => {

    return (
        <div className={styles.supporters_container}>
            <img className={styles.vrct_supporters_title} src={vrct_supporters_title} />
            <p className={styles.vrct_supporters_desc}>{`VRCT3.0のアップデートに向けて、めちゃ大変な開発を支えてくれた "Early Supporters" です。\nThey are the 'Early Supporters' who supported us through the incredibly challenging development toward the VRCT3.0 update.`}</p>
            <ProgressBar />
            <SupportsWrapper />
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

const SupportsWrapper = () => {
    const { saveScrollPosition, restoreScrollPosition } = useSettingBoxScrollPosition();
    const [imagesState, setImagesState] = useState({
        mogu_images: [],
        mochi_images: [],
        fuwa_images: [],
        basic_images: [],
        former_images: [],
        and_you_images: [],
        chato_images: [],
    });

    const shuffleImages = () => {
        saveScrollPosition();
        const getCategoryImages = (start, count) => {
            const category_images = supporters_filenames.slice(start, start + count);
            return shuffleArray(category_images);
        };

        const randomChatoImages = shuffleArray(
            Array.from({ length: mogu_count + mochi_count + fuwa_count + basic_count + former_count }, () =>
                getRandomImage(chato_expressions_filenames)
            )
        );

        setImagesState({
            mogu_images: getCategoryImages(0, mogu_count),
            mochi_images: getCategoryImages(mogu_count, mochi_count),
            fuwa_images: getCategoryImages(mogu_count + mochi_count, fuwa_count),
            basic_images: getCategoryImages(mogu_count + mochi_count + fuwa_count, basic_count),
            former_images: getCategoryImages(mogu_count + mochi_count + fuwa_count + basic_count, former_count),
            and_you_images: getCategoryImages(mogu_count + mochi_count + fuwa_count + basic_count + former_count, and_you_count),
            chato_images: randomChatoImages,
        });
        setTimeout(() => restoreScrollPosition(), 0);
    };

    useEffect(() => {
        shuffleImages();
        const interval = setInterval(() => {
            shuffleImages();
        }, SHUFFLE_INTERVAL_TIME);

        return () => clearInterval(interval);
    }, []);


    const getSupportersImageByFileName = (file_name) => {
        const image_path = Object.keys(supporter_images).find((path) => path.endsWith(file_name + ".png"));
        return image_path ? supporter_images[image_path]?.default : null;
    };

    const getChatoImageByFileName = (file_name) => {
        const image_path = Object.keys(chato_expression_images).find((path) => path.endsWith(file_name + ".png"));
        return image_path ? chato_expression_images[image_path]?.default : null;
    };

    const getRandomDelay = (min, max) => {
        const random_value = Math.random() * (max - min) + min;
        return `${random_value.toFixed(1)}s`;
    };


    const renderImages = (image_list, chato_list, options = {}) => {
        return image_list.map((file_name, index) => {
            const img_src = getSupportersImageByFileName(file_name);
            const is_default_icon = default_icon_numbers.some((element) => file_name.endsWith(element));
            const chato_expression_src = is_default_icon ? getChatoImageByFileName(chato_list[index]) : null;
            const random_delay = getRandomDelay(0.1, 6);

            return img_src ? (
                <div
                    key={file_name}
                    className={clsx(styles.supporter_image_wrapper, options.class_name)}
                    style={{ "--delay": random_delay }}
                >
                    <img className={styles.supporter_image} src={img_src} />
                    {chato_expression_src && (
                        <img
                            className={styles.default_chato_expression_image}
                            src={chato_expression_src}
                        />
                    )}
                    {options.is_and_you_icon ? <AndYouIcon /> : null}
                </div>
            ) : null;
        });
    };

    return (
        <div className={styles.supporters_wrapper}>
            {renderImages(imagesState.mogu_images, imagesState.chato_images, { class_name: styles.mogu_image })}
            {renderImages(imagesState.mochi_images, imagesState.chato_images)}
            {renderImages(imagesState.fuwa_images, imagesState.chato_images)}
            {renderImages(imagesState.basic_images, imagesState.chato_images)}
            {renderImages(imagesState.former_images, imagesState.chato_images)}
            <a href="https://vrct-dev.fanbox.cc/" target="_blank" rel="noreferrer">
                {renderImages(imagesState.and_you_images, imagesState.chato_images, { is_and_you_icon: true, class_name: styles.and_you_image })}
            </a>
        </div>
    );
};

const AndYouIcon = () => {
    return (
        <>
            <div className={styles.and_you_container}>
                <div className={styles.and_you_1}></div>
                <div className={styles.and_you_2}></div>
            </div>
            <p className={styles.and_you_fanbox_link_text}>
                FANBOX
                <ExternalLink className={styles.external_link_svg} />
            </p>
        </>
    );
};