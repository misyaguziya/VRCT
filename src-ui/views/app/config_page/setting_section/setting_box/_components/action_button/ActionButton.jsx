import styles from "./ActionButton.module.scss";

export const ActionButton = ({IconComponent, onclickFunction}) => {
    return (
        <div className={styles.container}>
            <button className={styles.button_wrapper} onClick={onclickFunction}>
                <IconComponent className={styles.button_svg}/>
            </button>
        </div>
    );
};