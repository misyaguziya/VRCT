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
    ColorEntryWithSaveButton,
    HotkeysEntry,
    RadioButton,
    AuthKey,
    ActionButton,
    WordFilter,
    WordFilterListToggleComponent,
    DownloadModels,
    MessageFormat,
    ConnectionCheckButton,
} from "../_components";
import { Checkbox } from "@common_components";
import { useI18n } from "@useI18n";

export const DropdownMenuContainer = (props) => {
    return (
        <TemplatesContainerWrapper {...props}>
            <LabelComponent label={props.label} desc={props.desc} />
            <DropdownMenu {...props} />
        </TemplatesContainerWrapper>
    );
};

export const MultiDropdownMenuContainer = (props) => {
    const { currentIsBreakPoint } = useStore_IsBreakPoint();

    return (
        <TemplatesContainerWrapper {...props}>
            <LabelComponent label={props.label} desc={props.desc} />
            <MultiDropdownMenu dropdown_settings={props.dropdown_settings} is_break_point={currentIsBreakPoint.data} />
        </TemplatesContainerWrapper>
    );
};

const TemplatesContainerWrapper = ({
    children,
    add_break_point = true,
    flex_column = false,
    remove_border_bottom = false,
    setting_id,
    label,
    ...rest
}) => {
    const { currentIsBreakPoint } = useStore_IsBreakPoint();

    const container_class = clsx(styles.container, {
        [styles.is_break_point]: add_break_point && currentIsBreakPoint.data,
        [styles.flex_column]: flex_column,
        [styles.remove_border_bottom]: remove_border_bottom,
    });

    const target_setting_id = setting_id ?? rest.dropdown_id ?? rest.hotkey_id ?? rest.name ?? rest.id;
    const target_label = typeof label === "string" ? label : undefined;

    return (
        <div
            className={container_class}
            data-setting-id={target_setting_id || undefined}
            data-setting-label={target_label || undefined}
        >
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
    setting_id,
    ...props
}) => {
    const { currentIsBreakPoint } = useStore_IsBreakPoint();

    const target_setting_id = setting_id ?? props.setting_id ?? props.hotkey_id ?? props.dropdown_id ?? props.name ?? props.id;

    const container_wrapper_props = {
        add_break_point: add_break_point,
        flex_column: flex_column,
        remove_border_bottom: remove_border_bottom,
        setting_id: target_setting_id,
        label: props.label,
    };

    if (label_type === "label_component") {
        return (
            <TemplatesContainerWrapper {...container_wrapper_props}>
                <LabelComponent {...props} />
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
                <LabelComponent {...props} />
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
export const ColorEntryWithSaveButtonContainer = (props) => (
    <CommonContainer Component={ColorEntryWithSaveButton} {...props} add_break_point={false} />
);

export const HotkeysEntryContainer = (props) => (
    <CommonContainer Component={HotkeysEntry} {...props} />
);

export const RadioButtonContainer = (props) => (
    <CommonContainer Component={RadioButton} {...props} />
);

export const AuthKeyContainer = (props) => {
    const { t } = useI18n();

    return (
        <CommonContainer
            Component={AuthKey}
            webpage_url={props.webpage_url}
            open_webpage_label={t("config_page.common.open_auth_key_webpage")}
            {...props}
        />
    );
};

export const ActionButtonContainer = (props) => (
    <CommonContainer Component={ActionButton} {...props} add_break_point={false}/>
);



export const WordFilterContainer = (props) => {
    return (
        <div data-setting-id={props.setting_id || "mic_word_filter"}>
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
        </div>
    );
};

export const DownloadModelsContainer = (props) => (
    <CommonContainer Component={DownloadModels} {...props} />
);

export const ConnectionCheckButtonContainer = (props) => (
    <CommonContainer Component={ConnectionCheckButton} {...props} />
);

export const MessageFormatContainer = (props) => {
    return (
        <div data-setting-id={props.setting_id}>
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
        </div>
    );
};
