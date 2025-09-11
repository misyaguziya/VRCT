import clsx from "clsx";
import styles from "./PosterShowcaseWorldsContents.module.scss";
import { useStore_PosterShowcaseWorldPageIndex } from "@store";
const images = import.meta.glob("@images/about_vrct/showcased_worlds/*.{png,jpg,jpeg,svg}", { eager: true });

const getImageByFileName = (file_name) => {
    const imagePath = Object.keys(images).find((path) => path.endsWith(file_name + ".png"));
    return imagePath ? images[imagePath]?.default : null;
};

import poster_showcase_worlds_settings from "./poster_showcase_worlds_settings";
import { chunkArray } from "@utils";

export const PosterShowcaseWorldsContents = () => {
    const { currentPosterShowcaseWorldPageIndex } = useStore_PosterShowcaseWorldPageIndex();
    const poster_showcase_world_images = poster_showcase_worlds_settings.map((setting) => ({
        img: getImageByFileName(setting.image_file_name),
        x_post_num: setting.x_post_num
    }));

    const chunked_poster_showcase_world_images = chunkArray(poster_showcase_world_images, 8);
    const target_poster_showcase_world_images = chunked_poster_showcase_world_images[currentPosterShowcaseWorldPageIndex.data];


    return (
        <div className={styles.container}>
            <div className={styles.poster_showcase_world_container}>
                {target_poster_showcase_world_images.map((poster, index) => {
                    const class_names = clsx(styles.poster_showcase_world_wrapper, {
                        [styles.clickable]: (poster.x_post_num !== null)
                    });

                    const content = (
                        <div className={styles.poster_showcase_world_img} >
                            <img style={ {height: "100%", width: "100%", "objectFit": "contain" }} src={poster.img} />
                        </div>
                    );
                    if (poster.x_post_num !== null) {
                        return (
                            <a href={`https://x.com/Shiina_12siy/status/${poster.x_post_num}`} target="_blank" rel="noreferrer" className={class_names} key={index}>
                                {content}
                            </a>
                        );
                    } else {
                        return (
                            <div className={class_names} key={index}>
                                {content}
                            </div>
                        );
                    }
                })}
            </div>
            <PosterShowcaseWorldsPagination page_length={chunked_poster_showcase_world_images.length}/>
        </div>
    );
};

import chat_white_square from "@images/chato_white_square.png";
import { useEffect } from "react";
import { randomIntMinMax } from "@utils";
const PosterShowcaseWorldsPagination = ({ page_length }) => {
    const { currentPosterShowcaseWorldPageIndex, updatePosterShowcaseWorldPageIndex } = useStore_PosterShowcaseWorldPageIndex();

    useEffect(() => {
        updatePosterShowcaseWorldPageIndex(randomIntMinMax(page_length -1));
    },[page_length]);

    const setPage = (index) => {
        updatePosterShowcaseWorldPageIndex(index);
    };

    const getClassNames = (index, baseClass) => clsx(baseClass, {
        [styles.is_active]: (currentPosterShowcaseWorldPageIndex.data === index),
    });

    return (
        <div className={styles.pagination_container}>
            {[...Array(page_length).keys()].map((index) => {
                return (
                    <div key={index} className={getClassNames(index, styles.pagination_box)} onClick={() => setPage(index)}>
                        <div className={styles.chato_box}>
                            <img src={chat_white_square} className={getClassNames(index, styles.pagination_chato_img)}/>
                        </div>
                        <div className={styles.indicator_box}>
                            <div className={getClassNames(index, styles.indicator)}></div>
                            <p className={getClassNames(index, styles.pagination_num)}>{index + 1}</p>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};