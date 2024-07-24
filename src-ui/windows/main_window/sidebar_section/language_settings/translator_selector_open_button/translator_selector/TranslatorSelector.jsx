import styles from "./TranslatorSelector.module.scss";
import { chunkArray } from "@utils/chunkArray";

import { useTranslatorList, useSelectedTranslator, useOpenedTranslatorSelector } from "@store";
export const TranslatorSelector = () => {
    const { currentTranslatorList } = useTranslatorList();
    const columns = chunkArray(currentTranslatorList, 2);

    return (
        <div className={styles.container}>
            <div className={styles.wrapper}>
                {columns.map((column, column_index) => (
                    <div className={styles.column_wrapper} key={`column_${column_index}`}>
                        {column.map(({ translator_key, translator_name, is_available }) => (
                            <TranslatorBox
                                key={translator_key}
                                translator_id={translator_key}
                                translator_name={translator_name}
                                is_available={is_available}
                            />
                        ))}
                    </div>
                ))}
            </div>
        </div>
    );
};

import clsx from "clsx";
const TranslatorBox = (props) => {
    const { currentSelectedTranslator, updateSelectedTranslator} = useSelectedTranslator();
    const { updateOpenedTranslatorSelector} = useOpenedTranslatorSelector();

    const box_class_name = clsx(
        styles.box,
        { [styles["is_selected"]]: (currentSelectedTranslator === props.translator_id) ? true : false },
        { [styles["is_available"]]: (props.is_available === true) ? true : false }
    );

    const selectTranslator = () => {
        updateSelectedTranslator(props.translator_id);
        updateOpenedTranslatorSelector(false);
    };
    return (
        <div className={box_class_name} onClick={selectTranslator}>
            <p className={styles.translator_name}>{props.translator_name}</p>
        </div>
    );
};