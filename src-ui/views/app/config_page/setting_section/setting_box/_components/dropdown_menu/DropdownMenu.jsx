import styles from "./DropdownMenu.module.scss";
import { _DropdownMenu } from "../_atoms/_dropdown_menu/_DropdownMenu";

export const DropdownMenu = (props) => {
    return (
        <div className={styles.container}>
            <_DropdownMenu {...props} />
        </div>
    );
};