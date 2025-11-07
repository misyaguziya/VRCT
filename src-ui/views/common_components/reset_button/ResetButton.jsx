import styles from "./ResetButton.module.scss";
import RedoSvg from "@images/redo.svg?react";

export const ResetButton = ({ onClickFunction }) => {
    return (
        <button className={styles.reset_button} onClick={onClickFunction}>
            <RedoSvg className={styles.reset_svg}/>
        </button>
    );
};