import React, { useEffect, useRef } from "react";
import { usePlugins } from "@logics_configs";
import clsx from "clsx";

if (typeof window !== "undefined") {
    window.React = React;
    window.clsx = clsx;
}

export const PluginsController = ({ fetchPluginsHasRunRef }) => {
    const {
        asyncLoadAllPlugins,
        asyncFetchPluginsInfo,
        currentPluginsData,
        updatePluginsData,
        currentSavedPluginsStatus,
    } = usePlugins();

    useEffect(() => {
        const loadPlugins = async () => {
            try {
                await asyncLoadAllPlugins();
                const info_array = await asyncFetchPluginsInfo();
                updatePluginsData(prev => {
                    // Map を利用してそれぞれの配列を plugin_id で参照できるようにする
                    const infoMap = new Map(info_array.map(info => [info.plugin_id, info]));
                    const prevMap = new Map(prev.data.map(item => [item.plugin_id, item]));

                    // info_array にある各アイテムについて、prev.data に同じ plugin_id があればマージ
                    const merged = info_array.map(info => {
                        if (prevMap.has(info.plugin_id)) {
                            return { ...info, ...prevMap.get(info.plugin_id) };
                        }
                        return info;
                    });

                    // prev.data にのみ存在するアイテムを追加し、is_outdated: true を付与
                    prev.data.forEach(item => {
                        if (!infoMap.has(item.plugin_id)) {
                            merged.push({ ...item, is_outdated: true });
                        }
                    });

                    return merged;
                });
            } catch (error) {
                console.error(error);
            }
        };

        if (!fetchPluginsHasRunRef.current) {
            loadPlugins();
        }
        return () => fetchPluginsHasRunRef.current = true;
    }, []);


    useEffect(() => {
        updatePluginsData(prev => {
            // currentSavedPluginsStatus.data の各要素を Map 化して plugin_id で参照
            const savedMap = new Map(currentSavedPluginsStatus.data.map(saved => [saved.plugin_id, saved]));
            const prevMap = new Map(prev.data.map(item => [item.plugin_id, item]));

            // prev.data にある各アイテムについて、保存済みの状態情報があればマージ
            const merged = prev.data.map(item => {
                if (savedMap.has(item.plugin_id)) {
                    return { ...item, is_enabled: savedMap.get(item.plugin_id).is_enabled };
                }
                return item;
            });

            // currentSavedPluginsStatus.data にのみ存在する項目があれば追加
            currentSavedPluginsStatus.data.forEach(saved => {
                if (!prevMap.has(saved.plugin_id)) {
                    merged.push({ plugin_id: saved.plugin_id, is_enabled: saved.is_enabled });
                }
            });

            return merged;
        });
    }, [currentSavedPluginsStatus]);



    return null;
};