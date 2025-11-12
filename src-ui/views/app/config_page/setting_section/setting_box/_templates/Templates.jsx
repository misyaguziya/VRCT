import clsx from "clsx";

import styles from "./Templates.module.scss";
import { useStore_IsOpenedDropdownMenu, useStore_IsBreakPoint } from "@store";
import {
    LabelComponent,
    DropdownMenu,
    MultiDropdownMenu,
    Slider,
    SwitchBox,
    Entry,
    EntryWithSaveButton,
    HotkeysEntry,
    RadioButton,
    OpenWebpage_DeeplAuthKey,
    DeeplAuthKey,
    ActionButton,
    ComputeDevice,
    WordFilter,
    WordFilterListToggleComponent,
    DownloadModels,
    MessageFormat,
} from "../_components";
import { Checkbox } from "@common_components";

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
        <TemplatesContainerWrapper onMouseLeaveFunction={onMouseLeaveFunction} {...props}>
            <LabelComponent label={props.label} desc={props.desc} />
            <DropdownMenu {...props} />
        </TemplatesContainerWrapper>
    );
};

export const MultiDropdownMenuContainer = (props) => {
    const { onMouseLeaveFunction } = useOnMouseLeaveDropdownMenu();

    return (
        <TemplatesContainerWrapper onMouseLeaveFunction={onMouseLeaveFunction} {...props}>
            <LabelComponent label={props.label} desc={props.desc} />
            <MultiDropdownMenu dropdown_settings={props.dropdown_settings} />
        </TemplatesContainerWrapper>
    );
};

const TemplatesContainerWrapper = ({
    children,
    add_break_point = true,
    flex_column = false,
    remove_border_bottom = false,
    onMouseLeaveFunction = null,
}) => {
    const { currentIsBreakPoint } = useStore_IsBreakPoint();

    const container_class = clsx(styles.container, {
        [styles.is_break_point]: add_break_point && currentIsBreakPoint.data,
        [styles.flex_column]: flex_column,
        [styles.remove_border_bottom]: remove_border_bottom,
    });

    return (
        <div className={container_class} onMouseLeave={onMouseLeaveFunction}>
            {children}
        </div>
    );
};

const CommonContainer = ({
    label_type = "label_component",
    add_break_point = true,
    flex_column = false,
    remove_border_bottom = false,
    Component,
    ...props
}) => {
    const { currentIsBreakPoint } = useStore_IsBreakPoint();

    const container_wrapper_props = {
        add_break_point: add_break_point,
        flex_column: flex_column,
        remove_border_bottom: remove_border_bottom,
    };

    if (label_type === "label_component") {
        return (
            <TemplatesContainerWrapper {...container_wrapper_props}>
                <LabelComponent label={props.label} desc={props.desc} />
                <Component {...props} is_break_point={currentIsBreakPoint.data} />
            </TemplatesContainerWrapper>
        );
    } else if (label_type === "no_label") {
        return (
            <TemplatesContainerWrapper {...container_wrapper_props}>
                <Component {...props} is_break_point={currentIsBreakPoint.data} />
            </TemplatesContainerWrapper>
        );
    } else if (label_type === "label_only") {
        return (
            <TemplatesContainerWrapper {...container_wrapper_props}>
                <LabelComponent label={props.label} desc={props.desc} />
            </TemplatesContainerWrapper>
        );
    }
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
export const EntryWithSaveButtonContainer = (props) => (
    <CommonContainer Component={EntryWithSaveButton} {...props} add_break_point={false} />
);

export const HotkeysEntryContainer = (props) => (
    <CommonContainer Component={HotkeysEntry} {...props} />
);

export const RadioButtonContainer = (props) => (
    <CommonContainer Component={RadioButton} {...props} />
);

export const DeeplAuthKeyContainer = (props) => {
    return (
        <TemplatesContainerWrapper>
            <div className={styles.deepl_auth_key_label_section}>
                <LabelComponent label={props.label} desc={props.desc} />
                <OpenWebpage_DeeplAuthKey />
            </div>
            <DeeplAuthKey {...props} />
        </TemplatesContainerWrapper>
    );
};

export const ActionButtonContainer = (props) => (
    <CommonContainer Component={ActionButton} {...props} add_break_point={false}/>
);

export const ComputeDeviceContainer = (props) => (
    <CommonContainer Component={ComputeDevice} {...props} />
);

export const WordFilterContainer = (props) => {
    return (
        <>
            <CommonContainer
                Component={WordFilterListToggleComponent}
                remove_border_bottom={true}
                {...props}
            />
            <CommonContainer
                Component={WordFilter}
                label_type="no_label"
                {...props}
            />
        </>
    );
};

export const DownloadModelsContainer = (props) => (
    <CommonContainer Component={DownloadModels} {...props} />
);

export const MessageFormatContainer = (props) => {
    return (
        <>
            <CommonContainer
                remove_border_bottom={true}
                label_type="label_only"
                {...props}
            />
            <CommonContainer
                Component={MessageFormat}
                label_type="no_label"
                {...props}
            />
        </>
    );
};