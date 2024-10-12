import styles from "./ActionButton.module.scss";

export const ActionButton = ({IconComponent, OnclickFunction}) => {
    return (
        <div className={styles.container}>
            <button className={styles.button_wrapper} onClick={OnclickFunction}>
                <IconComponent className={styles.button_svg}/>
            </button>
        </div>
    );
};