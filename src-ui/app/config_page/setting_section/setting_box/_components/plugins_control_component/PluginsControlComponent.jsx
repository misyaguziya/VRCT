import {
    SwitchBox,
} from "../index";
import { _DownloadButton } from "../_atoms/_download_button/_DownloadButton";
import styles from "./PluginsControlComponent.module.scss";

export const PluginsControlComponent = ({ variable_state, plugin_status, toggleFunction, ...props }) => {
    const option = {
        id: plugin_status.plugin_id,
        is_pending: plugin_status.is_pending,
        is_downloaded: plugin_status.is_downloaded,
        data: plugin_status.is_enabled,
        state: variable_state,
        progress: null,
    };

    const adjustedToggleFunction = () => {
        toggleFunction(plugin_status.plugin_id);
    };

    let is_turn_on_able = false;
    if (plugin_status.is_downloaded && plugin_status.is_plugin_supported) {
        is_turn_on_able = true;
    }
    if (plugin_status.is_outdated) {
        is_turn_on_able = true;
    }

    return (
        <div className={styles.container}>
            {is_turn_on_able &&
                <SwitchBox
                    variable={option}
                    toggleFunction={adjustedToggleFunction}
                />}
            {plugin_status.is_plugin_supported ?
                <_DownloadButton
                    option={option}
                    downloadStartFunction={props.downloadStartFunction}
                />
            :
                <div className={styles.unavailable_text}>
                    Downloaded but outdated.
                </div>
            }
        </div>
    );
};