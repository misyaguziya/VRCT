import styles from "./useSettingBox.module.scss";
import { LabelComponent } from "./components/label_component/LabelComponent";
import { DropdownMenu } from "./components/dropdown_menu/DropdownMenu";
import { useOpenedDropdownMenu } from "@store";

export const useSettingBox = () => {
    const { updateOpenedDropdownMenu } = useOpenedDropdownMenu();

    const DropdownMenuContainer = (props) => {
        const onMouseLeaveFunction = () => {
            updateOpenedDropdownMenu("");
        };

        return (
            <div className={styles.container} onMouseLeave={onMouseLeaveFunction}>
                <LabelComponent label={props.label} desc={props.desc} />
                <DropdownMenu {...props}/>
            </div>
        );
    };

    return { DropdownMenuContainer };
};