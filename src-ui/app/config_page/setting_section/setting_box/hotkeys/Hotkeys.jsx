import { useHotkeys } from "@logics_configs";
import styles from "./Hotkeys.module.scss";
import { HotkeysEntryContainer } from "../_templates/Templates";
import { useTranslation } from "react-i18next";
export const Hotkeys = () => {
    return (
        <div className={styles.container}>
            <HotkeysBoxContainer />
        </div>
    );
};

const HotkeysBoxContainer = () => {
    const { t } = useTranslation();
    const { currentHotkeys, setHotkeys } = useHotkeys();

    return (
        <div className={styles.container}>
            <HotkeysEntryContainer
                label={t("config_page.hotkeys.toggle_vrct_visibility.label")}
                hotkey_id="toggle_vrct_visibility"
                value={currentHotkeys.data}
                state={currentHotkeys.state}
                setHotkeys={setHotkeys}
            />
            <HotkeysEntryContainer
                label={t("config_page.hotkeys.toggle_translation.label")}
                hotkey_id="toggle_translation"
                value={currentHotkeys.data}
                state={currentHotkeys.state}
                setHotkeys={setHotkeys}
            />
            <HotkeysEntryContainer
                label={t("config_page.hotkeys.toggle_transcription_send.label")}
                hotkey_id="toggle_transcription_send"
                value={currentHotkeys.data}
                state={currentHotkeys.state}
                setHotkeys={setHotkeys}
            />
            <HotkeysEntryContainer
                label={t("config_page.hotkeys.toggle_transcription_receive.label")}
                hotkey_id="toggle_transcription_receive"
                value={currentHotkeys.data}
                state={currentHotkeys.state}
                setHotkeys={setHotkeys}
            />
        </div>
    );
};
