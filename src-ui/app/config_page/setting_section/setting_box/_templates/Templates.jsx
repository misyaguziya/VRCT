import clsx from "clsx";

import styles from "./Templates.module.scss";
import { useStore_IsOpenedDropdownMenu, useStore_IsBreakPoint } from "@store";
import {
    LabelComponent,
    DropdownMenu,
    Slider,
    SwitchBox,
    Entry,
    RadioButton,
    OpenWebpage_DeeplAuthKey,
    DeeplAuthKey,
    ActionButton,
    WordFilter,
    WordFilterListToggleComponent,
    DownloadModels,
} from "../_components/";
import { Checkbox } from "@common_components";

const LabeledContainer = ({ children, label, desc, custom_class_name }) => (
    <div className={clsx(styles.container, custom_class_name)}>
        <LabelComponent label={label} desc={desc} />
        {children}
    </div>
);

export const useOnMouseLeaveDropdownMenu = () => {
    const { updateIsOpenedDropdownMenu } = useStore_IsOpenedDropdownMenu();

    const onMouseLeaveFunction = () => {
        updateIsOpenedDropdownMenu("");
    };

    return { onMouseLeaveFunction };
};

export const DropdownMenuContainer = (props) => {
    const { onMouseLeaveFunction } = useOnMouseLeaveDropdownMenu();
    return (
        <div className={styles.container} onMouseLeave={onMouseLeaveFunction}>
            <LabelComponent label={props.label} desc={props.desc} />
            <DropdownMenu {...props} />
        </div>
    );
};

const CommonContainer = ({ Component, ...props }) => {
    const { currentIsBreakPoint } = useStore_IsBreakPoint();

    const container_class = clsx(styles.container, {
        [styles.is_break_point]: props.add_break_point ?? currentIsBreakPoint.data,
    });

    return (
        <LabeledContainer label={props.label} desc={props.desc} custom_class_name={container_class}>
            <Component {...props} />
        </LabeledContainer>
    );
};
export const SliderContainer = (props) => (
    <CommonContainer Component={Slider} {...props} />
);

export const CheckboxContainer = (props) => (
    <CommonContainer Component={Checkbox} {...props} add_break_point={false} />
);

export const SwitchBoxContainer = (props) => (
    <CommonContainer Component={SwitchBox} {...props} add_break_point={false}/>
);

export const EntryContainer = (props) => (
    <CommonContainer Component={Entry} {...props} add_break_point={false} />
);

export const RadioButtonContainer = (props) => (
    <CommonContainer Component={RadioButton} {...props} />
);

export const DeeplAuthKeyContainer = (props) => {
    const { currentIsBreakPoint } = useStore_IsBreakPoint();
    const container_class = clsx(styles.container, {
        [styles.is_break_point]: currentIsBreakPoint.data,
    });

    return (
        <div className={container_class}>
            <div className={styles.deepl_auth_key_label_section}>
                <LabelComponent label={props.label} desc={props.desc} />
                <OpenWebpage_DeeplAuthKey />
            </div>
            <DeeplAuthKey {...props} />
        </div>
    );
};

export const ActionButtonContainer = (props) => (
    <CommonContainer Component={ActionButton} {...props} add_break_point={false}/>
);

export const WordFilterContainer = (props) => (
    <div className={styles.word_filter_container}>
        <div className={styles.word_filter_switch_section}>
            <div className={styles.word_filter_label_wrapper}>
                <LabelComponent label={props.label} desc={props.desc} />
            </div>
            <WordFilterListToggleComponent />
        </div>
        <div className={styles.word_filter_section}>
            <WordFilter {...props} />
        </div>
    </div>
);

export const DownloadModelsContainer = (props) => (
    <CommonContainer Component={DownloadModels} {...props} />
);