import clsx from "clsx";
import styles from "./TranslatorSelector.module.scss";
import { chunkArray } from "@utils";

import { useStore_IsOpenedTranslatorSelector } from "@store";
import { useLanguageSettings } from "@logics_main";

export const TranslatorSelector = ({selected_id, translation_engines}) => {
    const columns = chunkArray(translation_engines, 2);

    return (
        <div className={styles.container}>
            <div className={styles.wrapper}>
                {columns.map((column, column_index) => (
                    <div className={styles.column_wrapper} key={`column_${column_index}`}>
                        {column.map(({ id, label, is_available }) => (
                            <TranslatorBox
                                key={id}
                                id={id}
                                label={label}
                                is_available={is_available}
                                is_selected={(id === selected_id)}
                            />
                        ))}
                    </div>
                ))}
            </div>
        </div>
    );
};

const TranslatorBox = (props) => {
    const { currentSelectedPresetTabNumber, currentSelectedTranslationEngines, setSelectedTranslationEngines} = useLanguageSettings();
    const { updateIsOpenedTranslatorSelector} = useStore_IsOpenedTranslatorSelector();

    const box_class_name = clsx(
        styles.box,
        { [styles["is_selected"]]: (currentSelectedTranslationEngines.data[currentSelectedPresetTabNumber.data] === props.id) ? true : false },
        { [styles["is_available"]]: (props.is_available === true) ? true : false }
    );

    const selectTranslator = () => {
        setSelectedTranslationEngines(props.id);
        updateIsOpenedTranslatorSelector(false);
    };
    return (
        <div className={box_class_name} onClick={selectTranslator}>
            <p className={styles.translator_name}>{props.label}</p>
        </div>
    );
};