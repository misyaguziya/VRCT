import { useStore_IsOpenedConfigPage } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useIsOpenedConfigPage = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentIsOpenedConfigPage, updateIsOpenedConfigPage } = useStore_IsOpenedConfigPage();

    const setIsOpenedConfigPage = (is_opened) => {
        updateIsOpenedConfigPage(is_opened);
        // if (is_opened) {
        //     asyncStdoutToPython("/set/enable/config_window");
        // } else {
        //     asyncStdoutToPython("/set/disable/config_window");
        // }
    };

    return {
        currentIsOpenedConfigPage,
        setIsOpenedConfigPage,
        updateIsOpenedConfigPage,
    };
};