import styles from "./EntryWithSaveButton.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";
import { _SaveButton } from "../_atoms/_save_button/_SaveButton";

export const EntryWithSaveButton = (props) => {
    const onChangeFunction = (e) => {
        props.onChangeFunction?.(e.target.value);
    };
    const saveFunction = () => {
        props.saveFunction();
    };
    const is_disabled = props.state === "pending";

    const handleEnterPressed = (e) => {
        if (is_disabled) return;
        saveFunction();
        e.target.blur();
    };

    return (
        <div className={styles.container}>
            <_Entry width={props.width} type={props.type} onChange={onChangeFunction} onEnterPressed={handleEnterPressed} ui_variable={props.variable} is_disabled={is_disabled}/>
            <_SaveButton onClick={saveFunction} is_disabled={is_disabled} />
        </div>
    );
};