import { useEffect, useRef, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { usePlugins } from "@logics_configs";
import styles from "./Plugins.module.scss";
import { PluginsControlComponent } from "../_components/plugins_control_component/PluginsControlComponent";
import { useNotificationStatus } from "@logics_common";
import ExternalLink from "@images/external_link.svg?react";

export const Plugins = () => {
    const {
        asyncFetchPluginsInfo,
    } = usePlugins();
    const hasRunRef = useRef(false);

    useEffect(() => {
        if (!hasRunRef.current) {
            asyncFetchPluginsInfo();
        }
        return () => hasRunRef.current = true;
    }, []);

    return (
        <div className={styles.container}>
            <PluginDownloadContainer />
        </div>
    );
};

const PluginDownloadContainer = () => {
    const { t, i18n } = useTranslation();
    const {
        downloadAndExtractPlugin,
        currentPluginsData,
        currentSavedPluginsStatus,
        toggleSavedPluginsStatus,
        handlePendingPlugin,
        currentFetchedPluginsInfo,
    } = usePlugins();
    const { showNotification_Success, showNotification_Error } = useNotificationStatus();

    // ダウンロード開始時の状態更新処理
    const downloadStartFunction = async (target_plugin_id) => {
        handlePendingPlugin(target_plugin_id, true);
        showNotification_Success(t("plugin_notifications.downloading"));

        const target_plugin_info = currentPluginsData.data.find(
            (d) => d.plugin_id === target_plugin_id
        );
        downloadAndExtractPlugin(target_plugin_info).then(() => {
            handlePendingPlugin(target_plugin_id, false);
            showNotification_Success(t("plugin_notifications.downloaded_success"));
        }).catch(error => {
            console.error(error);
            showNotification_Error(t("plugin_notifications.downloaded_error"));
        });
    };

    // プラグインのオンオフ切り替え処理
    const toggleFunction = (target_plugin_id) => {
        toggleSavedPluginsStatus(target_plugin_id);
    };

    const variable_state = currentSavedPluginsStatus.state;

    const filtered_plugins_data = currentPluginsData.data.filter(plugin => !plugin.is_outdated)

    // plugin_id で ABC 順にソート
    const sorted_plugins_data = filtered_plugins_data.sort((a, b) =>
        a.plugin_id.localeCompare(b.plugin_id)
    );

    // Duplicate
    const is_failed_to_fetch = currentFetchedPluginsInfo.state === "error";
    const is_fetching = currentFetchedPluginsInfo.state === "pending";

    return (
        <div className={styles.plugins_list_container}>
            {is_failed_to_fetch && <p>Failed to fetch plugins data</p>}
            {is_fetching && <p>Fetching plugins data...</p>}
            {sorted_plugins_data.map((plugin) => {
                const target_info = plugin.is_downloaded
                    ? plugin.downloaded_plugin_info
                    : plugin.latest_plugin_info;

                const target_locale = target_info.locales && target_info.locales[i18n.language]
                ? target_info.locales[i18n.language]
                : {
                    title: target_info.title,
                    desc: target_info.desc || null,
                };
                const homepage_link = plugin.latest_plugin_info?.homepage_link;

                return (
                    <div key={plugin.plugin_id} className={styles.plugin_wrapper}>
                        <div className={styles.labels_wrapper}>
                            <p className={styles.title}>
                                {target_locale.title}
                            </p>
                            <p className={styles.desc}>
                                {target_locale.desc}
                            </p>
                            {/* <p className={styles.plugin_id}>{plugin.plugin_id}</p> */}
                            {homepage_link && <HomepageLinkButton homepage_link={homepage_link}/>
                            }
                        </div>
                        <div className={styles.plugin_info_wrapper}>
                            {plugin.is_error ? (
                                <p style={{ color: "red" }}>Error: {plugin.error_message}</p>
                            ) : (
                                <PluginsControlComponent
                                    variable_state={variable_state}
                                    toggleFunction={toggleFunction}
                                    downloadStartFunction={downloadStartFunction}
                                    plugin_status={plugin}
                                />
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

const HomepageLinkButton = ({ homepage_link, speed = 40 /* px/s */ }) => {
    const containerRef = useRef(null);
    const textRef = useRef(null);
    const [inlineStyle, setInlineStyle] = useState({});

    const handleMouseEnter = useCallback(() => {
        const container = containerRef.current;
        const text = textRef.current;
        if (!container || !text) return;
        const overflow = text.scrollWidth - container.clientWidth;
        if (overflow > 0) {
            const duration = overflow / speed;
            setInlineStyle({
                transform: `translateX(-${overflow}px)`,
                transition: `transform ${duration}s linear`,
            });
        }
    }, [speed]);

    const handleMouseLeave = useCallback(() => {
        setInlineStyle({
            transform: 'translateX(0)',
            transition: 'transform 0.3s ease-out',
        });
    }, []);

    return (
        <div className={styles.open_homepage_button_wrapper}>
            <a
                className={styles.open_homepage_button}
                href={homepage_link}
                target="_blank"
                rel="noreferrer"
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
            >
                <div className={styles.text_container} ref={containerRef}>
                    <p
                    className={styles.open_homepage_text}
                    ref={textRef}
                    style={inlineStyle}
                    >
                    {homepage_link}
                    </p>
                </div>
                <ExternalLink className={styles.external_link_svg} />
            </a>
        </div>
    );
};