import styles from "./UpdatingComponent.module.scss";
import { useI18n } from "@useI18n";
import CircularProgress from "@mui/material/CircularProgress";
import chat_white_square from "@images/chato_white_square.png";

export const UpdatingComponent = () => {
    const { t } = useI18n();

    return (
        <div className={styles.container}>
            <div className={styles.chato_box}>
                <img src={chat_white_square} className={styles.chato_img}/>
            </div>
            <div className={styles.circular_box}>
                <CircularProgress size="20rem" sx={{
                    color: "var(--primary_300_color)",
                }}/>
            </div>
            <p className={styles.label}>{t("main_page.updating")}</p>
        </div>
    );
};