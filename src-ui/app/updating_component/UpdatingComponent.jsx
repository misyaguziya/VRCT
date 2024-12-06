import styles from "./UpdatingComponent.module.scss";
import { useTranslation } from "react-i18next";
import CircularProgress from "@mui/material/CircularProgress";
import chat_white_square from "@images/chato_white_square.png";

export const UpdatingComponent = () => {
    const { t } = useTranslation();

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
            <p className={styles.label}>{t("main_page.confirmation_message.updating")}</p>
        </div>
    );
};