import { useEffect } from "react";
import { usePlugins } from "@logics_configs";

export const MergeSavedPluginsStatusController = () => {
    const {
        updatePluginsData,
        currentSavedPluginsStatus,
    } = usePlugins();

    useEffect(() => {
        updatePluginsData(prev => {
            // currentSavedPluginsStatus.data の各要素を Map 化して plugin_id で参照
            const saved_map = new Map(currentSavedPluginsStatus.data.map(saved => [saved.plugin_id, saved]));
            const prev_map = new Map(prev.data.map(item => [item.plugin_id, item]));
            // prev.data にある各アイテムについて、保存済みの状態情報があればマージ
            const merged = prev.data.map(item => {

                if (saved_map.has(item.plugin_id)) {
                    return { ...item, is_enabled: saved_map.get(item.plugin_id).is_enabled };
                }
                return item;
            });

            // currentSavedPluginsStatus.data にのみ存在する項目があれば追加
            currentSavedPluginsStatus.data.forEach(saved => {
                if (!prev_map.has(saved.plugin_id)) {
                    merged.push({ plugin_id: saved.plugin_id, is_enabled: saved.is_enabled });
                }
            });
            return merged;
        });
    }, [currentSavedPluginsStatus]);

    return null;
};