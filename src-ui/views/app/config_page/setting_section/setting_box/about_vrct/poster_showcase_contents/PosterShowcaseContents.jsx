import styles from "./PosterShowcaseContents.module.scss";
import { PostersContents } from "./posters_contents/PostersContents";
import { PosterShowcaseWorldsContents } from "./poster_showcase_worlds_contents/PosterShowcaseWorldsContents";

export const PosterShowcaseContents = () => {
    return (
        <div className={styles.container}>
            <PosterShowcaseWorldsContents />
            <PostersContents />
        </div>
    );
};