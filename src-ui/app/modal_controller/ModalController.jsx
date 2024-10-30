import styles from "./ModalController.module.scss";
import { useStore_OpenedQuickSetting } from "@store";
import { Vr } from "@setting_box";
export const ModalController = () => {
    const { currentOpenedQuickSetting, updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    if (currentOpenedQuickSetting.data === "") return null;
    return (
        <div className={styles.container}>
            <div className={styles.bg_onclick_close_area} onClick={() => updateOpenedQuickSetting("")}></div>
            <div className={styles.wrapper}>
                <Vr />
            </div>
        </div>
    );
};