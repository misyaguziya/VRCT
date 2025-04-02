import { SwitchBox } from "../index";
import { _DownloadButton } from "../_atoms/_download_button/_DownloadButton";
import styles from "./PluginsControlComponent.module.scss";

export const PluginsControlComponent = ({ variable_state, plugin_status, toggleFunction, downloadStartFunction }) => {
    const { plugin_id, is_pending, is_downloaded, is_enabled, is_latest_version_available, is_plugin_supported, is_outdated } = plugin_status;

    const option = {
        id: plugin_id,
        is_pending: is_pending,
        is_downloaded: is_downloaded,
        data: is_enabled,
        update_button: is_downloaded && is_latest_version_available,
        state: variable_state,
        progress: null,
    };

    const togglePlugin = () => toggleFunction(plugin_id);
    const is_turn_on_able = is_downloaded && (is_plugin_supported || is_outdated);

    return (
        <div className={styles.container}>
            {is_plugin_supported ? (
                <_DownloadButton option={option} downloadStartFunction={downloadStartFunction} />
            ) : (
                <div className={styles.unavailable_text}>Downloaded but outdated.</div>
            )}
            {is_turn_on_able && <SwitchBox variable={option} toggleFunction={togglePlugin} />}
        </div>
    );
};