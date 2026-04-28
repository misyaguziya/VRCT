import styles from "./Entry.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";

export const Entry = (props) => {
    return (
        <div className={styles.entry_container}>
            <_Entry {...props} />
        </div>
    );
};