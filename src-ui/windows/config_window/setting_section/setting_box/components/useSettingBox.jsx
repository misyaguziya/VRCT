import styles from "./useSettingBox.module.scss";
import { useIsOpenedDropdownMenu } from "@store";

import { LabelComponent } from "./label_component/LabelComponent";
import { DropdownMenu } from "./dropdown_menu/DropdownMenu";
import { Slider } from "./slider/Slider";
import { Checkbox } from "./checkbox/Checkbox";
import { Switchbox } from "./switchbox/Switchbox";
import { Entry } from "./entry/Entry";
import { ThresholdComponent } from "./threshold_component/ThresholdComponent";
import { RadioButton } from "./radio_button/RadioButton";

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

    const SliderContainer = (props) => {
        return (
            <div className={styles.container}>
                <LabelComponent label={props.label} desc={props.desc} />
                <Slider {...props}/>
            </div>
        );
    };

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

    const ThresholdContainer = (props) => {
        return (
            <div className={styles.threshold_container}>
                <div className={styles.threshold_switch_section}>
                    <LabelComponent label={props.label} desc={props.desc} />
                    <Switchbox {...props}/>
                </div>
                <div className={styles.threshold_section}>
                    <ThresholdComponent {...props}/>
                </div>
            </div>
        );
    };

    return {
        DropdownMenuContainer,
        SliderContainer,
        CheckboxContainer,
        SwitchboxContainer,
        EntryContainer,
        ThresholdContainer,
        RadioButtonContainer,
    };
};