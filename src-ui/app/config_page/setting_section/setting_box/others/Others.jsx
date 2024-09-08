import { useTranslation } from "react-i18next";
import { useSettingBox } from "../components/useSettingBox";
// import {
//     useEnableAutoClearMessageBox,
// } from "@store";

import { useConfig } from "@logics/useConfig";

export const Others = () => {
    const { t } = useTranslation();
    const {
        CheckboxContainer,
        RadioButtonContainer,
    } = useSettingBox();

    const { currentEnableAutoClearMessageBox, toggleEnableAutoClearMessageBox } = useConfig();


    return (
        <>
            <CheckboxContainer
                label={t("config_page.auto_clear_the_message_box.label")}
                variable={currentEnableAutoClearMessageBox}
                toggleFunction={toggleEnableAutoClearMessageBox}
            />

            {/* <RadioButtonContainer label={t("config_page.send_message_button_type.label")} checkbox_id="checkbox_id_1"/> */}
        </>
    );
};