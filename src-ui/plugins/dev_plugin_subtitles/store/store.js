const store_hooks = {};

export const initStore = (createAtomWithHook) => {
    Object.assign(store_hooks, {
        // useStore_CountPluginState: createAtomWithHook(
        //     { count: 10 },
        //     "CountPluginState"
        // ).useHook,

        // useStore_AnotherState: createAtomWithHook(
        //     { value: "initial" },
        //     "AnotherState"
        // ).useHook,

        useStore_IsSubtitlePlaying: createAtomWithHook(false, "IsSubtitlePlaying", { is_state_ok: true }).useHook,
        useStore_SubtitlePlaybackMode: createAtomWithHook("relative", "SubtitlePlaybackMode", { is_state_ok: true }).useHook,
        useStore_SubtitleAbsoluteTargetTime: createAtomWithHook({
            hour: "23",
            minute: "00",
        }, "SubtitleAbsoluteTargetTime", { is_state_ok: true }).useHook,
        useStore_IsCuesScheduled: createAtomWithHook(false, "IsCuesScheduled", { is_state_ok: true }).useHook,
        useStore_CountdownAdjustment: createAtomWithHook(0, "CountdownAdjustment", { is_state_ok: true }).useHook,
        useStore_EffectiveCountdown: createAtomWithHook(null, "EffectiveCountdown", { is_state_ok: true }).useHook,
        useStore_SubtitleCues: createAtomWithHook([], "SubtitleCues", { is_state_ok: true }).useHook,

        useStore_SubtitleTimers: createAtomWithHook([], "SubtitleTimers", { is_state_ok: true }).useHook,
        useStore_SubtitleCountdownTimerId: createAtomWithHook([], "SubtitleCountdownTimerId", { is_state_ok: true }).useHook,
        useStore_SubtitleFileName: createAtomWithHook("ファイルが選択されていません", "SubtitleFileName", { is_state_ok: true }).useHook,
    });
};

export const useStore = (hook_name) => {
    if (!store_hooks[hook_name]) {
        throw new Error(`Hook ${hook_name} is not initialized.`);
    }
    return store_hooks[hook_name]();
};


// StoreContext.js
import React, { createContext, useContext } from "react";

export const StoreContext = createContext(null);

export const useStoreContext = () => {
    return useContext(StoreContext);
};
