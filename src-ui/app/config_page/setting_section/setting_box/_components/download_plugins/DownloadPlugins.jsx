import {
    SwitchBox,
} from "../index";
import { _DownloadButton } from "../_atoms/_download_button/_DownloadButton";
import styles from "./DownloadPlugins.module.scss";

export const DownloadPlugins = ({plugin_info, plugin_status, ...props}) => {
    const option = {
        id: plugin_info.plugin_id,
        is_pending: plugin_info.is_pending,
        is_downloaded: plugin_info.is_downloaded,
        progress: null,
    };


    return (
        <div className={styles.container}>
            {plugin_info.is_downloaded && plugin_info.is_plugin_supported &&
                <SwitchBox
                    variable={plugin_status}
                    toggleFunction={plugin_status.toggleFunction}
                />}
            {plugin_info.is_plugin_supported ?
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