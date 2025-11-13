import { useI18n } from "@useI18n";
import styles from "./WordFilter.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";
import { useState } from "react";
import { useStore_IsOpenedMicWordFilterList } from "@store";
import { useTranscription } from "@logics_configs";

export const WordFilter = () => {
    const { t } = useI18n();

    const [input_value, setInputValue] = useState("");
    const { currentMicWordFilterList, updateMicWordFilterList, setMicWordFilterList } = useTranscription();
    const { currentIsOpenedMicWordFilterList, updateIsOpenedMicWordFilterList } = useStore_IsOpenedMicWordFilterList();

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
                    const exists = updated_list.find((item) => item === each_input_value);
                    if (!exists) {
                        updated_list = [...updated_list, each_input_value];
                    }
                }
            }
            setMicWordFilterList(updated_list);
            return updated_list;
        });

        updateIsOpenedMicWordFilterList(true);
        setInputValue("");
    };


    const deleteAction = (target_item_value) => {
        updateMicWordFilterList((prev_list) => {
            const updated_list = prev_list.data.filter((item) => item !== target_item_value);
            setMicWordFilterList(updated_list);
            return updated_list;
        });
    };


    return (
        <div className={styles.container}>
            { currentIsOpenedMicWordFilterList.data && currentMicWordFilterList.data.length > 0 &&
                <div className={styles.list_section_wrapper}>
                    {
                        currentMicWordFilterList.data.map((item, index) => {
                            return <WordFilterItem value={item} key={index} deleteAction={deleteAction}/>;
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
import clsx from "clsx";
const WordFilterItem = (props) => {
    const item_wrapper_class_names = clsx(styles["item_wrapper"]);
    const item_text_class_names = clsx(styles["item_text"]);

    return (
        <div className={item_wrapper_class_names}>
            <p className={item_text_class_names}>{props.value}</p>
            <button className={clsx(styles.action_button, styles.delete)} onClick={() => props.deleteAction(props.value)}>
                <DeleteSvg className={styles.delete_svg}/>
            </button>
        </div>
    );
};

import ArrowLeftSvg from "@images/arrow_left.svg?react";
export const WordFilterListToggleComponent = () => {
    const { t } = useI18n();
    const { currentIsOpenedMicWordFilterList, updateIsOpenedMicWordFilterList } = useStore_IsOpenedMicWordFilterList();
    const { currentMicWordFilterList } = useTranscription();

    const svg_class_names = clsx(styles["arrow_left_svg"], {
        [styles.to_down]: !currentIsOpenedMicWordFilterList.data,
        [styles.to_up]: currentIsOpenedMicWordFilterList.data
    });

    const OnclickFunction = () => {
        updateIsOpenedMicWordFilterList(!currentIsOpenedMicWordFilterList.data);
    };

    return (
        <div className={styles.toggle_button_container}>
            <p className={styles.words_count_text}>{t("config_page.transcription.mic_word_filter.count_desc", {count: currentMicWordFilterList.data.length} )}</p>
            <button className={styles.toggle_button_wrapper} onClick={OnclickFunction}>
                <ArrowLeftSvg className={svg_class_names}/>
            </button>
        </div>
    );
};