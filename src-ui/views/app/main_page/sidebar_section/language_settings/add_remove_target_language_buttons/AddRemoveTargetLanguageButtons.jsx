import clsx from "clsx";
import styles from "./AddRemoveTargetLanguageButtons.module.scss";
import RemoveSvg from "@images/remove.svg?react";
import AddSvg from "@images/add.svg?react";

import { useLanguageSettings } from "@logics_main";

export const AddRemoveTargetLanguageButtons = () => {
    const {
        currentSelectedPresetTabNumber,
        // currentSelectedYourLanguages,
        currentSelectedTargetLanguages,
        removeTargetLanguage,
        addTargetLanguage,
    } = useLanguageSettings();

    const remove_button_class = clsx(styles.remove_target_language_button, {
        [styles.is_disabled]: !currentSelectedTargetLanguages.data[currentSelectedPresetTabNumber.data]["2"].enable,
    });
    const add_button_class = clsx(styles.add_target_language_button, {
        [styles.is_disabled]: currentSelectedTargetLanguages.data[currentSelectedPresetTabNumber.data]["3"].enable,
    });

    return (
        <div className={styles.add_remove_target_language_container}>
            <div className={remove_button_class} onClick={removeTargetLanguage}>
                <RemoveSvg className={styles.remove_svg} />
            </div>
            <div className={add_button_class} onClick={addTargetLanguage}>
                <AddSvg className={styles.add_svg} />
            </div>
        </div>
    );
};