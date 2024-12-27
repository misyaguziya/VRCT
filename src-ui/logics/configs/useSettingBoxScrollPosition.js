import { store, useStore_SettingBoxScrollPosition } from "@store";

export const useSettingBoxScrollPosition = () => {
    const { currentSettingBoxScrollPosition, updateSettingBoxScrollPosition, pendingSettingBoxScrollPosition } = useStore_SettingBoxScrollPosition();

    const saveScrollPosition = () => {
        if (store.setting_box_scroll_container.current) {
            updateSettingBoxScrollPosition(store.setting_box_scroll_container.current.scrollTop);
        }
    };
    const restoreScrollPosition = () => {

        if (store.setting_box_scroll_container.current) {
            updateSettingBoxScrollPosition((pre) => {
                store.setting_box_scroll_container.current.scrollTop = pre.data;
                return pre.data;
            })
        }

    };

    return {
        saveScrollPosition,
        restoreScrollPosition,
        currentSettingBoxScrollPosition,
        updateSettingBoxScrollPosition,
    };
};