import clsx from "clsx";
import styles from "./TranslatorSelector.module.scss";
import { chunkArray } from "@utils/chunkArray";

import { useStore_IsOpenedTranslatorSelector } from "@store";
import { useLanguageSettings } from "@logics_main";

export const TranslatorSelector = ({selected_translator_id, translation_engines}) => {
    const columns = (translation_engines.data !== undefined) ? chunkArray(translation_engines.data, 2) : [];

    return (
        <div className={styles.container}>
            <div className={styles.wrapper}>
                {columns.map((column, column_index) => (
                    <div className={styles.column_wrapper} key={`column_${column_index}`}>
                        {column.map(({ translator_id, translator_name, is_available }) => (
                            <TranslatorBox
                                key={translator_id}
                                translator_id={translator_id}
                                translator_name={translator_name}
                                is_available={is_available}
                                is_selected={(translator_id === selected_translator_id)}
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
        { [styles["is_selected"]]: (currentSelectedTranslationEngines.data[currentSelectedPresetTabNumber.data] === props.translator_id) ? true : false },
        { [styles["is_available"]]: (props.is_available === true) ? true : false }
    );

    const selectTranslator = () => {
        setSelectedTranslationEngines(props.translator_id);
        updateIsOpenedTranslatorSelector(false);
    };
    return (
        <div className={box_class_name} onClick={selectTranslator}>
            <p className={styles.translator_name}>{props.translator_name}</p>
        </div>
    );
};