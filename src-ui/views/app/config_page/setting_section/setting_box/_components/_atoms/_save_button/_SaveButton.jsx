import styles from "./_SaveButton.module.scss";
import { CircularProgress } from "@common_components";
import { useI18n } from "@useI18n";
import clsx from "clsx";

export const _SaveButton = ({
    onClick,
    is_disabled = false,
    label,
    className,
}) => {
    const { t } = useI18n();
    const button_label = label ?? t("config_page.common.save_button_label");

    const button_class_names = clsx(
        styles.save_button,
        { [styles.is_disabled]: is_disabled },
        className
    );

    return (
        <button
            type="button"
            className={button_class_names}
            onClick={onClick}
            disabled={is_disabled}
        >
            {is_disabled ? (
                <CircularProgress size="1.4rem" sx={{ color: "var(--dark_basic_text_color)" }} />
            ) : (
                <p className={styles.save_button_label}>{button_label}</p>
            )}
        </button>
    );
};
