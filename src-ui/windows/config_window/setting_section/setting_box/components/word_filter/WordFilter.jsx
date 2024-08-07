import styles from "./WordFilter.module.scss";
import { _Entry } from "../_atoms/_entry/_Entry";
import { useState } from "react";
import { useWordFilterList } from "@store";
export const WordFilter = () => {
    const [input_value, setInputValue] = useState();
    const { currentWordFilterList, updateWordFilterList } = useWordFilterList();

    const onChangeEntry = (e) => {
        setInputValue(e.target.value);
    };

    const addWords = () => {
        const input_value_array = input_value.split(",");

        let updated_list = [...currentWordFilterList];

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

        updateWordFilterList(updated_list);
    };


    const updateRedoable = (target_item_value, is_redoable) => {
        updateWordFilterList((prev_list) =>
            prev_list.map(item =>
                item.value === target_item_value ? { ...item, is_redoable: is_redoable } : item
            )
        );
    };

    const deleteAction = (target_item_value) => {
        updateRedoable(target_item_value, true);
    };

    const redoAction = (target_item_value) => {
        updateRedoable(target_item_value, false);
    };


    return (
        <div className={styles.container}>
            <div className={styles.list_section_wrapper}>
                {
                    currentWordFilterList.map((item, index) => {
                        return <WordFilterItem value={item.value} key={index} is_redoable={item.is_redoable} deleteAction={deleteAction} redoAction={redoAction}/>;
                    })
                }
            </div>
            <div className={styles.entry_section_wrapper}>
                <_Entry width="30rem" onChange={onChangeEntry}/>
                <button className={styles.add_button} onClick={addWords}>Add</button>
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