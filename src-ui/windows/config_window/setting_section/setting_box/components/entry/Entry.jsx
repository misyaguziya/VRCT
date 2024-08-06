import styles from "./Entry.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";

export const Entry = ({width}) => {

    const handleInputChange = (e) => {
        console.log(e.currentTarget.value);
    };

    return (
        <div className={styles.entry_container}>
            <_Entry width={width} onChange={handleInputChange} initialValue="" />
        </div>
    );
};