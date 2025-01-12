import { useHotkeys } from "@logics_configs";
import styles from "./Hotkeys.module.scss";
import { HotkeysEntryContainer } from "../_templates/Templates";

export const Hotkeys = () => {
    return (
        <div className={styles.container}>
            <HotkeysBoxContainer />
        </div>
    );
};

const HotkeysBoxContainer = () => {
    const { currentHotkeys, setHotkeys } = useHotkeys();
    return (
        <div className={styles.container}>
            <HotkeysEntryContainer
                // label={t("config_page.appearance.send_message_button_type.label")}
                label="Toggle active input box"
                hotkey_id="toggle_active_vrct"
                value={currentHotkeys.data}
                state={currentHotkeys.state}
                setHotkeys={setHotkeys}
            />
        </div>
    );
};
