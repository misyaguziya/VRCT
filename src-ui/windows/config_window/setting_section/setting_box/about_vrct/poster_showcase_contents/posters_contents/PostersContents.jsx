import clsx from "clsx";
import styles from "./PostersContents.module.scss";
import { useUiLanguage } from "@store";

import { useVrctPosterIndex } from "@store";
import ArrowLeftSvg from "@images/arrow_left.svg?react";

import iya_vrct_poster_ja from "@images/about_vrct/vrct_posters/iya_vrct_poster_ja.png";
import iya_vrct_poster_en from "@images/about_vrct/vrct_posters/iya_vrct_poster_en.png";
import iya_vrct_poster_cn from "@images/about_vrct/vrct_posters/iya_vrct_poster_cn.png";
import iya_vrct_poster_ko from "@images/about_vrct/vrct_posters/iya_vrct_poster_ko.png";
import iya_vrct_manga_ja from "@images/about_vrct/vrct_posters/iya_vrct_manga_ja.png";
import iya_vrct_manga_en from "@images/about_vrct/vrct_posters/iya_vrct_manga_en.png";
import iya_vrct_manga_ko from "@images/about_vrct/vrct_posters/iya_vrct_manga_ko.png";

const poster_images = [
    { img: iya_vrct_poster_ja, poster_type: "poster" },
    { img: iya_vrct_poster_en, poster_type: "poster" },
    { img: iya_vrct_poster_cn, poster_type: "poster" },
    { img: iya_vrct_poster_ko, poster_type: "poster" },
    { img: iya_vrct_manga_ja, poster_type: "manga" },
    { img: iya_vrct_manga_en, poster_type: "manga" },
    { img: iya_vrct_manga_ko, poster_type: "manga" },
];

import poster_images_authors_ja from "@images/about_vrct/vrct_posters/authors/poster_images_authors_ja.png";
import poster_images_authors_en from "@images/about_vrct/vrct_posters/authors/poster_images_authors_en.png";
import poster_images_authors_m_ja from "@images/about_vrct/vrct_posters/authors/poster_images_authors_m_ja.png";
import poster_images_authors_m_en from "@images/about_vrct/vrct_posters/authors/poster_images_authors_m_en.png";

export const PostersContents = () => {
    const { currentVrctPosterIndex, updateVrctPosterIndex } = useVrctPosterIndex();
    const { currentUiLanguage } = useUiLanguage();


    const updateIndex = (delta) => {
        const newIndex = (currentVrctPosterIndex + delta + poster_images.length) % poster_images.length;
        updateVrctPosterIndex(newIndex);
    };

    const current_poster = poster_images[currentVrctPosterIndex];
    const current_poster_authors_img_ja = (current_poster.poster_type === "poster") ? poster_images_authors_ja : poster_images_authors_m_ja;
    const current_poster_authors_img_en = (current_poster.poster_type === "poster") ? poster_images_authors_en : poster_images_authors_m_en;

    return (
        <div className={styles.poster_pagination_container}>
            <div className={styles.poster_pagination_wrapper}>
                <button
                    className={clsx(styles.poster_pagination_button, styles.poster_prev)}
                    onClick={() => updateIndex(-1)}
                    >
                    <ArrowLeftSvg className={clsx(styles.poster_pagination_svg, styles.poster_prev_svg)} />
                </button>
                <img src={current_poster.img} className={styles.poster_img} />
                <button
                    className={clsx(styles.poster_pagination_button, styles.poster_next)}
                    onClick={() => updateIndex(1)}
                    >
                    <ArrowLeftSvg className={clsx(styles.poster_pagination_svg, styles.poster_next_svg)} />
                </button>
            </div>
            {
                currentUiLanguage === "ja"
                ? <img src={current_poster_authors_img_ja} className={styles.poster_authors_img} />
                : <img src={current_poster_authors_img_en} className={styles.poster_authors_img} />
            }
        </div>
    );
};
