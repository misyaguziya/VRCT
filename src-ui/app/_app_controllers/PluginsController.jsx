import { useEffect } from "react";
import { usePlugins } from "@logics_configs";

// ホスト側でReactやjotaiをグローバル変数として提供
import ReactModule from "react";
if (typeof window !== "undefined") {
    window.React = ReactModule;
}

export const PluginsController = () => {
    const { loadAllPlugins } = usePlugins();
    useEffect(() => {
        loadAllPlugins();
    }, []);

    return null;
};