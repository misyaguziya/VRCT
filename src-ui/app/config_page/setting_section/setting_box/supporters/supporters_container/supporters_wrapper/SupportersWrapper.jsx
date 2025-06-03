import React, { useState, useCallback, useEffect } from "react";
import clsx from "clsx";
import Tooltip, { tooltipClasses } from '@mui/material/Tooltip';
import ArrowLeftSvg from "@images/arrow_left.svg?react";
import styles from "./SupportersWrapper.module.scss";
import { shuffleArray, randomIntMinMax, randomMinMax } from "@utils";

import {
    useSettingBoxScrollPosition,
    useSupporters,
} from "@logics_configs";

import { supporters_images_url } from "@ui_configs";

const SHUFFLE_INTERVAL_TIME = 20000;

const and_you_data = {
    supporter_id: "and_you",
};


const image_sets = {
    supporter_cards: `${supporters_images_url}/supporter_cards/`,
    chato_expressions: `${supporters_images_url}/chato_expressions/`,
    supporters_labels: `${supporters_images_url}/supporters_labels/`,
    supporters_icons: `${supporters_images_url}/supporters_icons/`,
};

const getSupporterCard = (plan_name) => {
    const card_map = {
        "mogu_2000": "mogu_card",
        "mochi_1000": "mochi_card",
        "fuwa_500": "fuwa_card",
        "basic_300": "basic_card",
    };
    if (!card_map[plan_name]) return `${image_sets.supporter_cards}basic_card.png`;

    return `${image_sets.supporter_cards}${card_map[plan_name]}.png`;
};

const getChatoExpressionsPath = (file_name) => `${image_sets.chato_expressions}${file_name}.png`;
const getSupportersLabelsPath = (file_name) => `${image_sets.supporters_labels}${file_name}.png`;
const getSupportersIconsPath = (file_name) => `${image_sets.supporters_icons}${file_name}.png`;


export const SupportersWrapper = () => {
    const { saveScrollPosition, restoreScrollPosition } = useSettingBoxScrollPosition();
    const { currentSupportersData } = useSupporters();

    const [json_data, setJsonData] = useState();
    const [supportersData, setSupportersData] = useState([]);
    const [chatoExpressions, setChatoExpressions] = useState([]);

    useEffect(() => {
        setJsonData(currentSupportersData.data);
    }, [currentSupportersData.data]);

    const supporters_settings = currentSupportersData.data.supporters_settings;
    const calc_support_period = supporters_settings.calc_support_period;
    const chato_ex_count = supporters_settings.chato_ex_count;

    const recalcAndUpdateSupporters = useCallback(() => {
        if (!json_data) return;

        const grouped_data = {
            mogu_2000: [],
            mochi_1000: [],
            fuwa_500: [],
            basic_300: [],
            former_supporter: [],
            and_you: [],
        };

        json_data.supporters_data.forEach((supporter) => {
            const value = supporter.highest_plan_during_the_period || "former_supporter";
            if (grouped_data[value]) {
                grouped_data[value].push(supporter);
            } else {
                grouped_data["former_supporter"].push(supporter);
            }
        });

        const newSupportersData = [
            ...shuffleArray(grouped_data["mogu_2000"]),
            ...shuffleArray(grouped_data["mochi_1000"]),
            ...shuffleArray(grouped_data["fuwa_500"]),
            ...shuffleArray(grouped_data["basic_300"]),
            ...shuffleArray(grouped_data["former_supporter"]),
            and_you_data,
        ];

        setSupportersData(newSupportersData);

        setChatoExpressions(
            newSupportersData.map(() =>
                getChatoExpressionsPath(
                    `chato_expression_${randomIntMinMax(1, chato_ex_count)}`
                )
            )
        );
    }, [json_data]);

    useEffect(() => {
        recalcAndUpdateSupporters();
    }, [json_data, recalcAndUpdateSupporters]);

    const shuffleSupporters = useCallback(() => {
        if (!json_data) return;
        saveScrollPosition();
        recalcAndUpdateSupporters();
        setTimeout(() => restoreScrollPosition(), 0);
    }, [json_data, recalcAndUpdateSupporters, saveScrollPosition, restoreScrollPosition]);

    useEffect(() => {
        const interval = setInterval(() => {
            shuffleSupporters();
        }, SHUFFLE_INTERVAL_TIME);

        return () => clearInterval(interval);
    }, [shuffleSupporters]);

    return (
        <div className={styles.container}>
            <ProgressBar />
            <div className={styles.supporters_wrapper}>
                <SupporterCardsComponent
                    supportersData={supportersData}
                    chatoExpressions={chatoExpressions}
                    calc_support_period={calc_support_period}
                />
            </div>
            <ProgressBar />
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

const SupporterCardsComponent = ({ supportersData, chatoExpressions, calc_support_period }) => {
    return supportersData.map((item, index) => {
        const target_plan = item.highest_plan_during_the_period;

        const img_src = getSupporterCard(target_plan);

        const is_and_you = item.supporter_id === "and_you";

        const random_delay = `${randomMinMax(0.1, 6).toFixed(1)}s`;

        const supporter_image_wrapper_classname = clsx(
            styles.supporter_image_wrapper,
            {
                [styles.mogu_image]: target_plan === "mogu_2000",
            }
        );

        return is_and_you ? (
            <a href="#support_us_container" key={item.supporter_id}>
                <div className={styles.supporter_image_container}>
                    <div
                        className={supporter_image_wrapper_classname}
                        style={{ "--delay": random_delay }}
                    >
                        <img
                            className={styles.supporter_image}
                            src={img_src}
                            alt="supporter"
                        />
                        <SupporterLabelComponent
                            target_plan={target_plan}
                            item={item}
                            chatoExpressions={chatoExpressions}
                        />
                        <AndYouIcon />
                    </div>
                </div>
            </a>
        ) : img_src ? (
            <div key={item.supporter_id} className={styles.supporter_image_container}>
                <div
                    className={supporter_image_wrapper_classname}
                    style={{ "--delay": random_delay }}
                >
                    <img
                        className={styles.supporter_image}
                        src={img_src}
                        alt="supporter"
                    />
                    <SupporterLabelComponent
                        target_plan={target_plan}
                        item={item}
                        chato_src={chatoExpressions[index]}
                        index={index}
                    />
                </div>
                <SupporterPeriodContainer settings={item} calc_support_period={calc_support_period}/>
            </div>
        ) : null;
    });
};

const SupporterLabelComponent = ({ item, target_plan, chato_src }) => {
    const is_icon_plan = ["mogu_2000", "mochi_1000"].includes(
        target_plan
    );

    const supporter_label_component_classname = clsx(
        styles.supporter_label_component,
        {
            [styles.is_icon_plan]: is_icon_plan,
        }
    );

    const is_and_you = item.supporter_id === "and_you";
    const is_default_icon = item.supporter_icon_id === "";

    const file_name = is_and_you ? "and_you" : `supporter_${item.supporter_id}`;
    const label_img_src = getSupportersLabelsPath(file_name);
    const icon_img_src = getSupportersIconsPath(
        `supporter_icon_${item.supporter_icon_id}`
    );

    return (
        <div className={supporter_label_component_classname}>
            {is_icon_plan && (
                <div className={styles.supporter_icon_wrapper}>
                    {is_default_icon ? (
                        <img
                            className={styles.default_chato_expression_image}
                            src={chato_src}
                            alt="chato expression"
                        />
                    ) : (
                        <img
                            className={styles.supporter_icon}
                            src={icon_img_src}
                            alt="supporter icon"
                        />
                    )}
                </div>
            )}
            <img
                className={styles.supporter_label_image}
                src={label_img_src}
                alt="supporter label"
            />
        </div>
    );
};

const SupporterPeriodContainer = ({ settings, calc_support_period }) => {
    const period_data = extractKeys(settings, calc_support_period);
    const offset = {
        popper: {
            sx: {
                [`&.${tooltipClasses.popper}[data-popper-placement*="top"] .${tooltipClasses.tooltip}`]: { marginBottom: "0.2em" },
            }
        }
    };

    return (
        <div className={styles.supporter_period_container}>
            <div className={styles.supporter_period_wrapper}>
                {Object.entries(period_data).map(([key, item], index) => {
                    if (item === "") return null;
                    const period_box_class_name = clsx(styles.period_box, {
                        [styles.mogu_bar]: item === "mogu_2000",
                        [styles.mochi_bar]: item === "mochi_1000",
                        [styles.fuwa_bar]: item === "fuwa_500",
                        [styles.basic_bar]: item === "basic_300",
                    });

                    return (
                        <Tooltip
                            key={index}
                            title={
                                <p className={styles.tooltip_period_label}>{key}</p>
                            }
                            placement="top"
                            slotProps={offset}
                        >
                            <div className={styles.period_box_wrapper}>
                                <div className={period_box_class_name}></div>
                            </div>
                        </Tooltip>
                    );
                })}
            </div>
        </div>
    );
};

const extractKeys = (data, keys_to_extract) => {
    const result = {};
    for (const key of keys_to_extract) {
        if (key in data) {
            result[key] = data[key];
        }
    }
    return result;
};


const ProgressBar = () => {
    const [is_active, setIsActive] = useState(false);
    useEffect(() => {
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                setIsActive(true);
            });
        });

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