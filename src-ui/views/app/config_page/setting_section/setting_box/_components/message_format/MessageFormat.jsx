import styles from "./MessageFormat.module.scss";
import { useTranslation } from "react-i18next";
import { _Entry } from "../_atoms/_entry/_Entry";
import SwapImg from "@images/swap_icon.png";
import ArrowLeftSvg from "@images/arrow_left.svg?react";
import {
    useStore_IsBreakPoint,
    useStore_MessageFormat_ExampleViewFilter,
} from "@store";
import { useAppearance } from "@logics_configs";
import { ui_configs } from "@ui_configs";
import { ResetButton } from "@common_components";
import { useState, useEffect, useRef } from "react";

const ENTRY_WIDTH = "8rem";

const EXAMPLE_TEXTS = {
    en: "Hello",
    ja: "こんにちは",
    ko: "안녕하세요",
    fr: "Bonjour",
};

export const MessageFormat = (props) => {
    const { currentIsBreakPoint } = useStore_IsBreakPoint();
    const message_format_container_class = clsx(styles.container, {
        [styles.is_break_point]: currentIsBreakPoint.data,
    });

    return (
        <div className={message_format_container_class}>
            <ExampleComponent
                format={props.variable.data}
                format_id={props.format_id}
            />
            <div className={styles.border}></div>
            <InputComponent
                variable={props.variable.data}
                setFunction={props.setFunction}
                format_id={props.format_id}
            />
        </div>
    );
};

const ExampleComponent = ({ format, format_id }) => {
    const { currentUiLanguage } = useAppearance();
    const { t } = useTranslation();
    const {
        currentMessageFormat_ExampleViewFilter,
        updateMessageFormat_ExampleViewFilter,
    } = useStore_MessageFormat_ExampleViewFilter();

    const locale_base_path = "config_page.others.message_format_common.example_view.";

    const label_title = t(locale_base_path + "title");

    const label_original_translated = t(locale_base_path + "original_translated");
    const label_original_translated_multi = t(locale_base_path + "original_translated_multi");
    const label_translated_only_multi = t(locale_base_path + "translated_only_multi");
    const label_translated_only = t(locale_base_path + "translated_only");
    const label_original_only = t(locale_base_path + "original_only");

    const createExampleMessage = (id) => {
        // 言語順序を決定
        let example_text_order = [];
        switch (currentUiLanguage.data) {
            case "ja":
                example_text_order = ["ja", "en", "ko", "fr"];
                break;
            case "ko":
                example_text_order = ["ko", "ja", "en", "fr"];
                break;
            default: // en
                example_text_order = ["en", "ja", "ko", "fr"];
                break;
        }

        const original = EXAMPLE_TEXTS[example_text_order[0]];
        const translations = example_text_order.slice(1).map(lang => EXAMPLE_TEXTS[lang]);

        const originalPart = `${format.message.prefix}${original}${format.message.suffix}`;
        const translationSingle = `${format.translation.prefix}${translations[0]}${format.translation.suffix}`;
        const translationMulti = `${format.translation.prefix}${translations.join(format.translation.separator)}${format.translation.suffix}`;

        switch (id) {
            case "original_translated":
                return format.translation_first
                    ? `${translationSingle}${format.separator}${originalPart}`
                    : `${originalPart}${format.separator}${translationSingle}`;

            case "original_only":
                return originalPart;

            case "translated_only":
                return translationSingle;

            case "translated_only_multi":
                return translationMulti;

            case "original_translated_multi":
                return format.translation_first
                    ? `${translationMulti}${format.separator}${originalPart}`
                    : `${originalPart}${format.separator}${translationMulti}`;

            default:
                throw new Error(`Unexpected id: ${id}`);
        }
    };

    const ExampleBox = ({label, example_text_id}) => {
        return (
            <div className={styles.example_wrapper}>
                <p className={styles.example_label}>{label}</p>
                <div className={styles.example_chatbox}>
                    <p className={styles.example_text}>{createExampleMessage(example_text_id)}</p>
                </div>
            </div>
        );

    };

    const svg_class_names = clsx(styles.arrow_left_svg, {
        [styles.to_down]: currentMessageFormat_ExampleViewFilter.data[format_id] === "Simplified",
        [styles.to_up]: currentMessageFormat_ExampleViewFilter.data[format_id] === "All"
    });


    const FilteredExampleBox = ({format_id, id}) => {
        if (format_id === "send" && id === "Simplified") {
            return (
                <>
                    <ExampleBox label={label_original_translated} example_text_id="original_translated" />
                    <ExampleBox label={label_original_translated_multi} example_text_id="original_translated_multi" />
                </>
            );
        } else if ( format_id === "send" && id === "All") {
            return (
                <>
                    <ExampleBox label={label_original_translated} example_text_id="original_translated" />
                    <ExampleBox label={label_original_translated_multi} example_text_id="original_translated_multi" />
                    <ExampleBox label={label_translated_only_multi} example_text_id="translated_only_multi" />
                    <ExampleBox label={label_translated_only} example_text_id="translated_only" />
                    <ExampleBox label={label_original_only} example_text_id="original_only" />
                </>
            );

        } else if (format_id === "received") {
            return (
                <>
                    <ExampleBox label={label_original_translated} example_text_id="original_translated" />
                    <ExampleBox label={label_original_only} example_text_id="original_only" />
                    <ExampleBox label={label_translated_only} example_text_id="translated_only" />
                </>
            );
        }
    };

    const exampleViewFilterToggleFunction = (format_id) => {
        if (["send", "received"].includes(format_id) === false) return console.error(`format_id should be small case 'send' or 'received'. got format_id: ${format_id}`);

        updateMessageFormat_ExampleViewFilter({
            ...currentMessageFormat_ExampleViewFilter.data,
            [format_id]: currentMessageFormat_ExampleViewFilter.data[format_id] === "Simplified"
                ? "All"
                : "Simplified"
        });
    };

    return (
        <div className={styles.example_container}>
            <p className={styles.section_title}>{label_title}</p>
            <div className={styles.example_view_container}>
                <FilteredExampleBox format_id={format_id} id={currentMessageFormat_ExampleViewFilter.data[format_id]} />
            </div>
            { format_id === "send" &&
                <div className={styles.show_more_container} onClick={() => exampleViewFilterToggleFunction(format_id)}>
                    <ArrowLeftSvg className={svg_class_names}/>
                </div>
            }
        </div>
    );
};


const InputComponent = ({id, variable, setFunction, format_id }) => {
    const { t } = useTranslation();

    const locale_base_path = "config_page.others.message_format_common.settings.";
    const label_title = t(locale_base_path + "title");

    const LABEL_ORIGINAL = t(locale_base_path + "original");
    const LABEL_TRANSLATED = t(locale_base_path + "translated");
    const LABEL_FOR_MULTI_TRANSLATION = t(locale_base_path + "for_multi_translation");

    const replaceValue = (value) => {
        if (value === "") return "";

        const replaced = value.replace(/\\n/g, "\n");
        return replaced;
    };

    const [local_var, setLocalVar] = useState(variable);
    const debounce_ref = useRef(null);

    useEffect(() => {
        setLocalVar(variable);
    }, [variable]);

    useEffect(() => {
        return () => {
            if (debounce_ref.current) {
                clearTimeout(debounce_ref.current);
                debounce_ref.current = null;
            }
        };
    }, []);

    const scheduleUpdate = (new_var) => {
        if (debounce_ref.current) clearTimeout(debounce_ref.current);
        debounce_ref.current = setTimeout(() => {
            setFunction(new_var);
            debounce_ref.current = null;
        }, 500);
    };

    const handleChange = (parent_key, child_key) => (e) => {
        const raw_value = e.target.value;
        const parsed_value = replaceValue(raw_value);

        if (child_key !== undefined) {
            const new_var = {
                ...local_var,
                [parent_key]: {
                    ...local_var[parent_key],
                    [child_key]: parsed_value,
                },
            };
            setLocalVar(new_var);
            scheduleUpdate(new_var);
        } else {
            const new_var = {
                ...local_var,
                [parent_key]: parsed_value,
            };
            setLocalVar(new_var);
            scheduleUpdate(new_var);
        }
    };

    const toUiValue = (v) => {
        if (typeof v === "string") {
            return v.replace(/\n/g, "\\n");
        }
        console.log("Empty");

        return v ?? "";
    };

    const resetFunction = () => {
        const new_val = format_id === "send" ? ui_configs.send_message_format_parts : ui_configs.received_message_format_parts;
        setLocalVar(new_val);
        setFunction(new_val);
    };

    const SwapButton = ({ variable, setFunction }) => {
        const swapMessageAndTranslate = () => {
            const new_var = { ...variable, translation_first: !variable.translation_first };
            setLocalVar(new_var);
            setFunction(new_var);
        };

        return (
            <div className={styles.swap_button_wrapper} onClick={swapMessageAndTranslate}>
                <p className={styles.swap_text}>{variable.translation_first ? LABEL_TRANSLATED : LABEL_ORIGINAL}</p>
                <img className={styles.swap_img} src={SwapImg} alt="Swap Icon" />
                <p className={styles.swap_text}>{variable.translation_first ? LABEL_ORIGINAL : LABEL_TRANSLATED}</p>
            </div>
        );
    };

    return (
        <div className={styles.message_format_settings_container}>
            <p className={styles.section_title}>{label_title}</p>
            <div className={styles.message_format_settings_wrapper}>
                <div className={styles.swap_button_container}>
                    <SwapButton variable={local_var} setFunction={setFunction} />
                </div>
                { !local_var.translation_first ?
                <div className={styles.input_wrapper}>
                    <div className={styles.input_contents}>
                        <_Entry ui_variable={toUiValue(local_var.message.prefix)} width={ENTRY_WIDTH} onChange={handleChange("message", "prefix")} />
                        <p className={styles.preset_text}>{LABEL_ORIGINAL}</p>
                        <_Entry ui_variable={toUiValue(local_var.message.suffix)} width={ENTRY_WIDTH} onChange={handleChange("message", "suffix")} />
                    </div>
                    <div className={styles.input_contents}>
                        <_Entry ui_variable={toUiValue(local_var.separator)} width={ENTRY_WIDTH} onChange={handleChange("separator")} />
                    </div>
                    <div className={styles.input_contents}>
                        <_Entry ui_variable={toUiValue(local_var.translation.prefix)} width={ENTRY_WIDTH} onChange={handleChange("translation", "prefix")} />
                        <p className={styles.preset_text}>{LABEL_TRANSLATED}</p>
                        <_Entry ui_variable={toUiValue(local_var.translation.suffix)} width={ENTRY_WIDTH} onChange={handleChange("translation", "suffix")} />
                    </div>
                </div>
                :
                <div className={styles.input_wrapper}>
                    <div className={styles.input_contents}>
                        <_Entry ui_variable={toUiValue(local_var.translation.prefix)} width={ENTRY_WIDTH} onChange={handleChange("translation", "prefix")} />
                        <p className={styles.preset_text}>{LABEL_TRANSLATED}</p>
                        <_Entry ui_variable={toUiValue(local_var.translation.suffix)} width={ENTRY_WIDTH} onChange={handleChange("translation", "suffix")} />
                    </div>
                    <div className={styles.input_contents}>
                        <_Entry ui_variable={toUiValue(local_var.separator)} width={ENTRY_WIDTH} onChange={handleChange("separator")} />
                    </div>
                    <div className={styles.input_contents}>
                        <_Entry ui_variable={toUiValue(local_var.message.prefix)} width={ENTRY_WIDTH} onChange={handleChange("message", "prefix")} />
                        <p className={styles.preset_text}>{LABEL_ORIGINAL}</p>
                        <_Entry ui_variable={toUiValue(local_var.message.suffix)} width={ENTRY_WIDTH} onChange={handleChange("message", "suffix")} />
                    </div>
                </div>
                }
                { format_id === "send" &&
                    <div className={styles.multi_translation_input_wrapper}>
                        <p className={styles.multi_translation_title}>{LABEL_FOR_MULTI_TRANSLATION}</p>
                        <div className={styles.input_contents}>
                            <p className={styles.preset_text}>{LABEL_TRANSLATED}</p>
                            <_Entry ui_variable={toUiValue(local_var.translation.separator)} width={ENTRY_WIDTH} onChange={handleChange("translation", "separator")} />
                            <p className={styles.preset_text}>{LABEL_TRANSLATED}</p>
                        </div>
                    </div>
                }
                <div className={styles.reset_button_wrapper}>
                    <ResetButton onClickFunction={resetFunction}/>
                </div>
            </div>
        </div>
    );
};