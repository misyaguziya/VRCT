import { useTranslation } from "react-i18next";
import styles from "./WordFilter.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";
import { useState } from "react";
import { useStore_IsOpenedMicWordFilterList } from "@store";
import { useMicWordFilterList } from "@logics_configs";

export const WordFilter = () => {
    const { t } = useTranslation();

    const [input_value, setInputValue] = useState("");
    const { currentMicWordFilterList, updateMicWordFilterList, setMicWordFilterList } = useMicWordFilterList();
    const { currentIsOpenedMicWordFilterList, updateIsOpenedMicWordFilterList } = useStore_IsOpenedMicWordFilterList();

    const extractRedoableFalseItem = (updated_list) => {
        return updated_list.filter(item => {
            if (item.is_redoable === false) return true;
        });
    };

    const onChangeEntry = (e) => {
        setInputValue(e.target.value);
    };

    const addWords = () => {
        if (input_value === undefined) return;
        updateMicWordFilterList((prev_list) => {
            const input_value_array = input_value.split(",");
            let updated_list = [...prev_list.data];
            for (let each_input_value of input_value_array) {
                each_input_value = each_input_value.trim();
                if (each_input_value) {
                    const target_item = updated_list.find((item) => item.value === each_input_value);
                    if (target_item === undefined) {
                        // Add
                        updated_list = [...updated_list, { value: each_input_value, is_redoable: false }];
                    } else {
                        // Update
                        updated_list = updated_list.map(item =>
                            item.value === each_input_value ? { ...item, is_redoable: false } : item
                        );
                    }
                }
            }
            const updated_list_for_restoring = extractRedoableFalseItem(updated_list).map((d) => d.value);
            setMicWordFilterList(updated_list_for_restoring);
            return updated_list;
        });

        updateIsOpenedMicWordFilterList(true);
        setInputValue("");
    };


    const updateRedoable = (target_item_value, is_redoable) => {
        updateMicWordFilterList((prev_list) => {
            const updated_list = prev_list.data.map(item =>
                item.value === target_item_value ? { ...item, is_redoable: is_redoable } : item
            );
            const updated_list_for_restoring = extractRedoableFalseItem(updated_list).map((d) => d.value);
            setMicWordFilterList(updated_list_for_restoring);
            return updated_list;
        });
    };

    const deleteAction = (target_item_value) => {
        updateRedoable(target_item_value, true);
    };

    const redoAction = (target_item_value) => {
        updateRedoable(target_item_value, false);
    };


    return (
        <div className={styles.container}>
            { currentIsOpenedMicWordFilterList.data &&
            <div className={styles.list_section_wrapper}>
                {
                    currentMicWordFilterList.data.map((item, index) => {
                        return <WordFilterItem value={item.value} key={index} is_redoable={item.is_redoable} deleteAction={deleteAction} redoAction={redoAction}/>;
                    })
                }
            </div>
            }
            <div className={styles.entry_section_wrapper}>
                <_Entry width="30rem" onChange={onChangeEntry} ui_variable={input_value}/>
                <button className={styles.add_button} onClick={addWords}>{t("config_page.transcription.mic_word_filter.add_button_label")}</button>
            </div>
        </div>
    );
};

import DeleteSvg from "@images/cancel.svg?react";
import RedoSvg from "@images/redo.svg?react";
import clsx from "clsx";
const WordFilterItem = (props) => {


    const item_wrapper_class_names = clsx(styles["item_wrapper"], {
        [styles["is_redoable"]]: props.is_redoable
    });

    const item_text_class_names = clsx(styles["item_text"], {
        [styles["is_redoable"]]: props.is_redoable
    });

    const target_item_value = props.value;

    return (
        <div className={item_wrapper_class_names}>
            <p className={item_text_class_names}>{target_item_value}</p>
            {props.is_redoable
            ?
                <button className={clsx(styles.action_button, styles.redo)} onClick={() => props.redoAction(target_item_value)}>
                    <RedoSvg className={styles.redo_svg}/>
                </button>
            :
                <button className={clsx(styles.action_button, styles.delete)} onClick={() => props.deleteAction(target_item_value)}>
                    <DeleteSvg className={styles.delete_svg}/>
                </button>
            }
        </div>
    );
};

import ArrowLeftSvg from "@images/arrow_left.svg?react";
export const WordFilterListToggleComponent = (props) => {
    const { t } = useTranslation();
    const { currentIsOpenedMicWordFilterList, updateIsOpenedMicWordFilterList } = useStore_IsOpenedMicWordFilterList();
    const { currentMicWordFilterList } = useMicWordFilterList();


    const svg_class_names = clsx(styles["arrow_left_svg"], {
        [styles.to_down]: !currentIsOpenedMicWordFilterList.data,
        [styles.to_up]: currentIsOpenedMicWordFilterList.data
    });

    const OnclickFunction = () => {
        updateIsOpenedMicWordFilterList(!currentIsOpenedMicWordFilterList.data);
    };

    const word_filter_list_length = currentMicWordFilterList.data.filter(item => item.is_redoable === false).length;


    return (
        <div className={styles.toggle_button_container}>
            <p className={styles.words_count_text}>{t("config_page.transcription.mic_word_filter.count_desc", {count: word_filter_list_length} )}</p>
            <button className={styles.toggle_button_wrapper} onClick={OnclickFunction}>
                <ArrowLeftSvg className={svg_class_names}/>
            </button>
        </div>
    );
};