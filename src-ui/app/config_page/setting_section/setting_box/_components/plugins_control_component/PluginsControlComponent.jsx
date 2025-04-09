import React from "react";
import { SwitchBox } from "../index";
import { _DownloadButton } from "../_atoms/_download_button/_DownloadButton";
import styles from "./PluginsControlComponent.module.scss";

// メインのコントロールコンポーネント。ダウンロード済み / 未ダウンロードで分岐して表示する
export const PluginsControlComponent = ({
    variable_state,
    plugin_status,
    toggleFunction,
    downloadStartFunction,
}) => {
    // 共通オプション（各子コンポーネントに引き回す情報）
    const option = {
        id: plugin_status.plugin_id,
        is_pending: plugin_status.is_pending,
        is_downloaded: plugin_status.is_downloaded,
        data: plugin_status.is_enabled,
        update_button: plugin_status.is_downloaded && plugin_status.is_latest_version_available,
        state: variable_state,
        progress: null,
    };

    if (plugin_status.is_downloaded) {
        return (
            <DownloadedPluginControl
                option={option}
                plugin_status={plugin_status}
                toggleFunction={toggleFunction}
                downloadStartFunction={downloadStartFunction}
            />
        );
    } else {
        return (
            <NotDownloadedPluginControl
                option={option}
                plugin_status={plugin_status}
                downloadStartFunction={downloadStartFunction}
            />
        );
    }
};

// -------------------------
// ダウンロード済みのプラグイン用コンポーネント
// 状態により以下の分岐を行う
// ・ is_latest_version_already が true なら「最新版を使用中」
// ・ is_latest_version_already が false かつ is_latest_version_available が true なら「最新版を利用可能」（アップデートボタン＋スイッチ）
// ・ それ以外（is_latest_version_already:false && is_latest_version_available: false）なら、desc等の情報とスイッチのみ表示
const DownloadedPluginControl = ({
    option,
    plugin_status,
    toggleFunction,
    downloadStartFunction,
}) => {
    // on/off トグル時の処理
    const togglePlugin = () => {
        toggleFunction(plugin_status.plugin_id);
    };


    // ダウンロード済みの場合、ダウンロードされた情報からタイトルやバージョンを取得
    const title = plugin_status.downloaded_plugin_info?.title || plugin_status.latest_plugin_info.title;
    const current_version =
        plugin_status.downloaded_plugin_info?.plugin_version || plugin_status.latest_plugin_info.plugin_version;

    // コンポーネントごとに表示内容を分岐
    if (plugin_status.is_latest_version_already) {
        // 最新版が既に使用中
        return (
            <div className={styles.container}>
                <p>{title}</p>
                <p>現在のバージョン: {current_version}</p>
                <p>最新版を使用中</p>
                <SwitchBox variable={option} toggleFunction={togglePlugin} />
            </div>
        );
    } else if (plugin_status.is_latest_version_available) {
        // 最新版の利用可能なお知らせとアップデートボタン＋スイッチ
        return (
            <div className={styles.container}>
                <p>{title}</p>
                <p>現在のバージョン: {current_version}</p>
                <p>最新版を利用可能</p>
                <_DownloadButton option={option} downloadStartFunction={downloadStartFunction} />
                <SwitchBox variable={option} toggleFunction={togglePlugin} />
            </div>
        );
    } else {
        // 最新版利用可能ではないがダウンロード済み
        // ※「desc」に関しては、情報があればplugin_status.descやlatest_plugin_info.descを利用してください
        const desc =
            plugin_status.latest_plugin_info.desc ||
            "追加情報がありません。";
        return (
            <div className={styles.container}>
                <p>{title}</p>
                <p>現在のバージョン: {current_version}</p>
                <p>{desc}</p>
                <SwitchBox variable={option} toggleFunction={togglePlugin} />
            </div>
        );
    }
};

// -------------------------
// 未ダウンロードのプラグイン用コンポーネント
// 状態により以下の分岐を行う
// ・ is_latest_version_available が true なら：info_title, 最新バージョン情報とダウンロードボタン
// ・ is_latest_version_available が false なら：info_title, 最新バージョン情報と「現在利用不可」
const NotDownloadedPluginControl = ({ option, plugin_status, downloadStartFunction }) => {
    const title = plugin_status.latest_plugin_info.title;
    const latest_version = plugin_status.latest_plugin_info.plugin_version;
    // ※未ダウンロードの場合、current_versionは「未ダウンロード」や「なし」といった扱いとする
    const current_version = "未ダウンロード";

    if (plugin_status.is_latest_version_available) {
        return (
            <div className={styles.container}>
                <p>{title}</p>
                <p>現在のバージョン: {current_version}</p>
                <p>最新バージョン: {latest_version}</p>
                <_DownloadButton option={option} downloadStartFunction={downloadStartFunction} />
            </div>
        );
    } else {
        return (
            <div className={styles.container}>
                <p>{title}</p>
                <p>現在のバージョン: {current_version}</p>
                <p>最新バージョン: {latest_version}</p>
                <p>現在利用不可</p>
            </div>
        );
    }
};
