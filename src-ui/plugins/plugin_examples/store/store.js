const store_hooks = {};

export const initStore = (createAtomWithHook) => {
    Object.assign(store_hooks, {
        useStore_CountPluginState: createAtomWithHook(
            { count: 10 },
            "CountPluginState"
        ).useHook,

        useStore_AnotherState: createAtomWithHook(
            { value: "initial" },
            "AnotherState"
        ).useHook,
    });
};

export const useStore = (hook_name) => {
    if (!store_hooks[hook_name]) {
        throw new Error(`Hook ${hook_name} is not initialized.`);
    }
    return store_hooks[hook_name]();
};