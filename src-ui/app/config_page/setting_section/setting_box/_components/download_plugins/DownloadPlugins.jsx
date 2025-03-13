import {
    SwitchBox,
} from "../index";
import { _DownloadButton } from "../_atoms/_download_button/_DownloadButton";

export const DownloadPlugins = ({plugin_info, ...props}) => {

    const option = {
        is_pending: plugin_info.is_pending,
        is_downloaded: plugin_info.is_downloaded,
    }
    console.log(plugin_info);


    return (
        <div>
            {/* <SwitchBox
                variable={currentEnableAutoMicSelect}
                toggleFunction={toggleEnableAutoMicSelect}
            /> */}
            {plugin_info.is_plugin_supported ?
                <_DownloadButton
                    option={option}
                    downloadStartFunction={props.downloadStartFunction}
                />
            :
                <div>
                    Unavailable
                </div>
            }
        </div>
    );
};