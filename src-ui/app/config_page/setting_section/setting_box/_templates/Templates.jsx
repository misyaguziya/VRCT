import styles from "./Templates.module.scss";
import { useStore_IsOpenedDropdownMenu } from "@store";

import {
    LabelComponent,
    DropdownMenu,
    Slider,
    Checkbox,
    SwitchBox,
    Entry,
    RadioButton,
    OpenWebpage_DeeplAuthKey,
    DeeplAuthKey,
    ActionButton,
    WordFilter,
    WordFilterListToggleComponent,
} from "../_components/";

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


export const SliderContainer = (props) => {
    return (
        <div className={styles.container}>
            <LabelComponent label={props.label} desc={props.desc} />
            <Slider {...props}/>
        </div>
    );
};

export const CheckboxContainer = (props) => {
    return (
        <div className={styles.container}>
            <LabelComponent label={props.label} desc={props.desc} />
            <Checkbox {...props}/>
        </div>
    );
};

export const SwitchBoxContainer = (props) => {
    return (
        <div className={styles.container}>
            <LabelComponent label={props.label} desc={props.desc} />
            <SwitchBox {...props}/>
        </div>
    );
};

export const EntryContainer = (props) => {
    return (
        <div className={styles.container}>
            <LabelComponent label={props.label} desc={props.desc} />
            <Entry {...props}/>
        </div>
    );
};

export const RadioButtonContainer = (props) => {
    return (
        <div className={styles.container}>
            <LabelComponent label={props.label} desc={props.desc} />
            <RadioButton {...props}/>
        </div>
    );
};

export const DeeplAuthKeyContainer = (props) => {
    return (
        <div className={styles.container}>
            <div className={styles.deepl_auth_key_label_section}>
                <LabelComponent label={props.label} desc={props.desc} />
                <OpenWebpage_DeeplAuthKey />
            </div>
            <DeeplAuthKey {...props}/>
        </div>
    );
};

export const ActionButtonContainer = (props) => {
    return (
        <div className={styles.container}>
            <LabelComponent label={props.label} desc={props.desc} />
            <ActionButton {...props}/>
        </div>
    );
};

export const WordFilterContainer = (props) => {
    return (
        <div className={styles.word_filter_container}>
            <div className={styles.word_filter_switch_section}>
                <div className={styles.word_filter_label_wrapper}>
                    <LabelComponent label={props.label} desc={props.desc}/>
                </div>
                <WordFilterListToggleComponent/>
            </div>
            <div className={styles.word_filter_section}>
                <WordFilter {...props}/>
            </div>
        </div>
    );
};