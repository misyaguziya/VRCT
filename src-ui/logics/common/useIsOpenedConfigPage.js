import { useStore_IsOpenedConfigPage } from "@store";

export const useIsOpenedConfigPage = () => {
    const { currentIsOpenedConfigPage, updateIsOpenedConfigPage } = useStore_IsOpenedConfigPage();

    const setIsOpenedConfigPage = (is_opened) => {
        updateIsOpenedConfigPage(is_opened);
    };

    return {
        currentIsOpenedConfigPage,
        setIsOpenedConfigPage,
        updateIsOpenedConfigPage,
    };
};