import { useEffect } from "react";
import styles from "./PluginCompatibilityList.module.scss";
import { usePlugins } from "@logics_configs";
import CheckMarkSvg from "@images/check_mark.svg?react";
import XSvg from "@images/x_mark.svg?react";
import WarningSvg from "@images/warning.svg?react";

export const PluginCompatibilityList = () => {
    const {
        enabledPluginsList,
        asyncFetchPluginsInfo,
    } = usePlugins();

    useEffect(() => {
        asyncFetchPluginsInfo();
    }, []);

    // ダウンロード済みのもの
    const downloaded_plugin = enabledPluginsList().filter(p => p.is_downloaded);

    const compatible_plugins_list = [];
    const incompatible_plugins_list = [];
    for (const p of downloaded_plugin) {
        if (!p.downloaded_plugin_info?.is_plugin_supported_latest_vrct && !p.latest_plugin_info?.is_plugin_supported_latest_vrct) {
            // プラグイン最新版でも、VRCT最新版（VRCTアプデ後）に非対応のもの
            incompatible_plugins_list.push(p);
        } else {
            // 現プラグイン or 最新版が、VRCT最新版（VRCTアプデ後）に対応しているもの
            compatible_plugins_list.push(p);
        }
    }

    const is_any_incompatible_plugin = incompatible_plugins_list.length > 0;
    const is_any_compatible_plugin = compatible_plugins_list.length > 0;

    if (!is_any_incompatible_plugin && !is_any_compatible_plugin) return null; // This is just for safety.

    return (
        <div className={styles.container}>
            <p className={styles.title}>使用中プラグインの互換性チェック</p>
            <div className={styles.plugins_compatibility_container}>
                {incompatible_plugins_list.map(plugin => {
                    const target_data = plugin.downloaded_plugin_info;
                    return <PluginContainer key={target_data.plugin_id} target_data={target_data} is_compatible={false}/>;
                })}
                {compatible_plugins_list.map(plugin => {
                    const target_data = plugin.downloaded_plugin_info;
                    return <PluginContainer key={target_data.plugin_id} target_data={target_data} is_compatible={true} />;
                })}
            </div>
            {is_any_incompatible_plugin &&
                <div className={styles.warning_container}>
                    <WarningSvg className={styles.warning_svg}/>
                    <p className={styles.warning_text}>VRCT最新バージョンで互換性のないプラグインはアップデート後に無効化されます。引き続き使用したい場合は、各プラグインの更新を待ってください。</p>
                </div>
            }
        </div>
    );
};

const PluginContainer = ({ target_data, is_compatible }) => {
    return (
        <div className={styles.plugin_box}>
            <p className={clsx(styles.plugin_label, {[styles.is_compatible]: is_compatible})} >{target_data.title}</p>
            {is_compatible
                ? <CheckMarkSvg className={styles.check_mark_svg}/>
                : <XSvg className={styles.x_svg}/>
            }
        </div>
    );
};