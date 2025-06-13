import semver from "semver";

import { useStore_SoftwareVersion, useStore_LatestSoftwareVersionInfo } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useSoftwareVersion = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentLatestSoftwareVersionInfo, updateLatestSoftwareVersionInfo } = useStore_LatestSoftwareVersionInfo();
    const { currentSoftwareVersion, updateSoftwareVersion, pendingSoftwareVersion } = useStore_SoftwareVersion();

    const getSoftwareVersion = () => {
        pendingSoftwareVersion();
        asyncStdoutToPython("/get/data/version");
    };

    const updateSoftwareVersionInfo = (payload) => {
        updateLatestSoftwareVersionInfo(prev => ({
            is_update_available: payload.is_update_available,
            new_version: payload.new_version || prev.data.new_version,
        }));
    };

    const isPluginCompatible = (main_version, lower_version, upper_version) => {
        // lower_version 以上かつ upper_version 以下なら互換性ありと判定
        return semver.gte(main_version, lower_version) && semver.lte(main_version, upper_version);
    };

    const checkVrctVerCompatibility = (min_version, max_version) => {
        const current_vrct_version = currentSoftwareVersion.data;
        const latest_vrct_version = currentLatestSoftwareVersionInfo.data.new_version;

        const is_plugin_supported = isPluginCompatible(current_vrct_version, min_version, max_version);
        const is_plugin_supported_latest_vrct = isPluginCompatible(latest_vrct_version, min_version, max_version);
        return { is_plugin_supported, is_plugin_supported_latest_vrct };
    };

    return {
        currentSoftwareVersion,
        getSoftwareVersion,
        updateSoftwareVersion,

        updateSoftwareVersionInfo,
        currentLatestSoftwareVersionInfo,
        updateLatestSoftwareVersionInfo,

        checkVrctVerCompatibility,
    };
};