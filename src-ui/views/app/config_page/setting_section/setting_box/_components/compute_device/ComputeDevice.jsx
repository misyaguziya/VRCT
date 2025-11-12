import styles from "./ComputeDevice.module.scss";
import { DropdownMenu } from "../_atoms/_dropdown_menu/_DropdownMenu";
import { ActionButton } from "../action_button/ActionButton";
import HelpSvg from "@images/help.svg?react";
import { useStore_OpenedQuickSetting } from "@store"

export const ComputeDevice = (props) => {
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();

    const onClickFunction = () => {
        updateOpenedQuickSetting("update_software");
    };

    return (
        <div className={styles.container}>
            <DropdownMenu
                {...props}
                is_disabled={true}
            />
            <ActionButton
                {...props}
                IconComponent={HelpSvg}
                onclickFunction={onClickFunction}
            />
        </div>
    );
};