import { useTranslation } from "react-i18next";
import plugin_info from "../plugin_info.json";

export const usePluginTranslation = () => {
    const ns = plugin_info.plugin_id;
    return useTranslation(ns);
};