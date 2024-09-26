import styles from "./useSettingBox.module.scss";
import { useStore_IsOpenedDropdownMenu } from "@store";
import clsx from "clsx";

import { LabelComponent } from "./label_component/LabelComponent";
import { DropdownMenu } from "./dropdown_menu/DropdownMenu";
import { Slider } from "./slider/Slider";
import { Checkbox } from "./checkbox/Checkbox";
import { Switchbox } from "./switchbox/Switchbox";
import { Entry } from "./entry/Entry";
import { RadioButton } from "./radio_button/RadioButton";
import { OpenWebpage_DeeplAuthKey, DeeplAuthKey } from "./deepl_auth_key/DeeplAuthKey";
import { ActionButton } from "./action_button/ActionButton";
import { WordFilter, WordFilterListToggleComponent } from "./word_filter/WordFilter";


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

export const useSettingBox = () => {

    const CheckboxContainer = (props) => {
        return (
            <div className={styles.container}>
                <LabelComponent label={props.label} desc={props.desc} />
                <Checkbox {...props}/>
            </div>
        );
    };

    const SwitchboxContainer = (props) => {
        return (
            <div className={styles.container}>
                <LabelComponent label={props.label} desc={props.desc} />
                <Switchbox {...props}/>
            </div>
        );
    };

    const EntryContainer = (props) => {
        return (
            <div className={styles.container}>
                <LabelComponent label={props.label} desc={props.desc} />
                <Entry {...props}/>
            </div>
        );
    };

    const RadioButtonContainer = (props) => {
        return (
            <div className={styles.container}>
                <LabelComponent label={props.label} desc={props.desc} />
                <RadioButton {...props}/>
            </div>
        );
    };

    const DeeplAuthKeyContainer = (props) => {
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

    const ActionButtonContainer = (props) => {
        return (
            <div className={styles.container}>
                <LabelComponent label={props.label} desc={props.desc} />
                <ActionButton {...props}/>
            </div>
        );
    };


    const WordFilterContainer = (props) => {
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

    return {
        CheckboxContainer,
        SwitchboxContainer,
        EntryContainer,
        RadioButtonContainer,
        DeeplAuthKeyContainer,
        WordFilterContainer,
        ActionButtonContainer,
    };
};