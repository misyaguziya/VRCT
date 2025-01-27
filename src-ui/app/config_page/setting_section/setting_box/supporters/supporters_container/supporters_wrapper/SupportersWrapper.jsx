import React, { useState, useCallback, useEffect } from "react";
import clsx from "clsx";
import ArrowLeftSvg from "@images/arrow_left.svg?react";
import styles from "./SupportersWrapper.module.scss";
import { shuffleArray, randomIntMinMax, randomMinMax } from "@utils";

import {
    useSettingBoxScrollPosition,
} from "@logics_configs"

import json_data from "./data.json";

const target_supporting_month = "2025-01";

const SHUFFLE_INTERVAL_TIME = 20000;



const and_you_data = {
    supporter_id: "and_you",
};


const getImagePath = (images, file_name) => {
    const image_path = Object.keys(images).find((path) => path.endsWith(`${file_name}.png`));
    return image_path ? images[image_path]?.default : null;
};

const image_sets = {
    supporter_cards: import.meta.glob("@images/supporters/supporter_cards/*.png", { eager: true }),
    chato_expressions: import.meta.glob("@images/supporters/chato_expressions/*.png", { eager: true }),
    supporters_labels: import.meta.glob("@images/supporters/supporters_labels/*.png", { eager: true }),
    supporters_icons: import.meta.glob("@images/supporters/supporters_icons/*.png", { eager: true }),
};

const getSupporterCard = (plan_name) => {
    const card_map = {
        "もぐもぐ_2000": "mogu_card",
        "もちもち_1000": "mochi_card",
        "ふわふわ_500": "fuwa_card",
        "Basic_300": "basic_card",
    };
    return getImagePath(image_sets.supporter_cards, card_map[plan_name] || "basic_card");
};

const getChatoExpressionsPath = (file_name) =>
    getImagePath(image_sets.chato_expressions, file_name);

const getSupportersLabelsPath = (file_name) =>
    getImagePath(image_sets.supporters_labels, file_name);

const getSupportersIconsPath = (file_name) =>
    getImagePath(image_sets.supporters_icons, file_name);

const chato_ex_count = Object.keys(image_sets.chato_expressions).length;

export const SupportersWrapper = () => {
    const { saveScrollPosition, restoreScrollPosition } = useSettingBoxScrollPosition();

    let credit_pending_count = 0;
    const filtered_data = json_data.filter((supporter) => {
        if (!supporter.supporter_id) return false;

        const months = Object.keys(supporter).filter((key) => key.match(/^\d{4}-\d{2}$/));
        const has_valid_month = months.some((month) => supporter[month]);
        if (!has_valid_month) return false;

        const basic_300_months = months.filter((month) => supporter[month] === "Basic_300");
        const has_special_plan = months.some((month) => ["ふわふわ_500", "もちもち_1000", "もぐもぐ_2000"].includes(supporter[month]));

        if (basic_300_months.length === 1 && !has_special_plan) {
            credit_pending_count++;
            return false;
        }

        return true;
    });

    const grouped_data = {
        もぐもぐ_2000: [],
        もちもち_1000: [],
        ふわふわ_500: [],
        Basic_300: [],
        empty: [],
        and_you: [],
    };

    filtered_data.forEach((supporter) => {
        const value = supporter[target_supporting_month] || "empty";
        if (grouped_data[value]) {
            grouped_data[value].push(supporter);
        } else {
            grouped_data["empty"].push(supporter);
        }
    });

    const [supportersData, setSupportersData] = useState(() => [
        ...grouped_data["もぐもぐ_2000"],
        ...grouped_data["もちもち_1000"],
        ...grouped_data["ふわふわ_500"],
        ...grouped_data["Basic_300"],
        ...grouped_data["empty"],
        and_you_data,
    ]);


    const [chatoExpressions, setChatoExpressions] = useState(() =>
        supportersData.map(() =>
            getChatoExpressionsPath(`chato_expression_${randomIntMinMax(1, chato_ex_count)}`)
        )
    );


    const shuffleSupporters = useCallback(() => {
        saveScrollPosition();
        const newSupportersData = [
            ...shuffleArray(grouped_data["もぐもぐ_2000"]),
            ...shuffleArray(grouped_data["もちもち_1000"]),
            ...shuffleArray(grouped_data["ふわふわ_500"]),
            ...shuffleArray(grouped_data["Basic_300"]),
            ...shuffleArray(grouped_data["empty"]),
            and_you_data,
        ];
        setSupportersData(newSupportersData);


        setChatoExpressions(
            newSupportersData.map(() =>
                getChatoExpressionsPath(`chato_expression_${randomIntMinMax(1, chato_ex_count)}`)
            )
        );
        setTimeout(() => restoreScrollPosition(), 0);
    }, [grouped_data]);

    const renderImages = () => {
        return supportersData.map((item, index) => {
            const target_plan = item[target_supporting_month];
            const img_src = getSupporterCard(target_plan);
            const is_default_icon = item.supporter_icon_id === "";
            const is_icon_plan = ["もぐもぐ_2000", "もちもち_1000"].includes(target_plan);
            const is_and_you = item.supporter_id === "and_you";

            const random_delay = `${randomMinMax(0.1, 6).toFixed(1)}s`;

            const image_wrapper_classname = clsx(styles.supporter_image_wrapper, {
                [styles.mogu_image]: target_plan === "もぐもぐ_2000",
            });

            const file_name = is_and_you ? "and_you" : `supporter_${item.supporter_id}`;
            const label_img_src = getSupportersLabelsPath(file_name);
            const icon_img_src = getSupportersIconsPath(`supporter_icon_${item.supporter_icon_id}`);

            const supporter_label_component_classname = clsx(styles.supporter_label_component, {
                [styles.is_icon_plan]: is_icon_plan,
            });

            const supporterLabelComponent = () => (
                <div className={supporter_label_component_classname}>
                    {is_icon_plan && (
                        <div className={styles.supporter_icon_wrapper}>
                            {is_default_icon ? (
                                <img
                                    className={styles.default_chato_expression_image}
                                    src={chatoExpressions[index]}
                                />
                            ) : (
                                <img className={styles.supporter_icon} src={icon_img_src} />
                            )}
                        </div>
                    )}
                    <img className={styles.supporter_label_image} src={label_img_src} />
                </div>
            );

            return is_and_you ? (
                <a href="#ttt">
                    <div
                        key={item.supporter_id}
                        className={image_wrapper_classname}
                        style={{ "--delay": random_delay }}
                    >
                        <img className={styles.supporter_image} src={img_src} />
                        {supporterLabelComponent()}
                        <AndYouIcon />
                    </div>
                </a>

            ): img_src ? (
                <div
                    key={item.supporter_id}
                    className={image_wrapper_classname}
                    style={{ "--delay": random_delay }}
                >
                    <img className={styles.supporter_image} src={img_src} />
                    {supporterLabelComponent()}
                </div>
            ) : null;
        });
    };


    useEffect(() => {
        shuffleSupporters();
        const interval = setInterval(() => {
            shuffleSupporters();
        }, SHUFFLE_INTERVAL_TIME);

        return () => clearInterval(interval);
    }, []);

    return (
        <div>
            <div className={styles.supporters_wrapper}>{renderImages()}</div>
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
                FANBOX Ko-fi Patreon
            </p>
            <ArrowLeftSvg className={styles.arrow_left_svg} />
        </>
    );
};