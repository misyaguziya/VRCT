import styles from "./useSettingBox.module.scss";
import { LabelComponent } from "./components/label_component/LabelComponent";
import { DropdownMenu } from "./components/dropdown_menu/DropdownMenu";
import { useIsOpenedDropdownMenu } from "@store";

export const useSettingBox = () => {
    const { updateIsOpenedDropdownMenu } = useIsOpenedDropdownMenu();

    const DropdownMenuContainer = (props) => {
        const onMouseLeaveFunction = () => {
            updateIsOpenedDropdownMenu("");
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