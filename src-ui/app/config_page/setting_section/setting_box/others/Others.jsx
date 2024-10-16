import { useTranslation } from "react-i18next";

import {
    useEnableAutoClearMessageInputBox,
} from "@logics_configs";

import {
    CheckboxContainer,
} from "../_templates/Templates";


export const Others = () => {
    return (
        <>
            <AutoClearMessageInputBoxContainer />
        </>
    );
};

const AutoClearMessageInputBoxContainer = () => {
    const { t } = useTranslation();
    const { currentEnableAutoClearMessageInputBox, toggleEnableAutoClearMessageInputBox } = useEnableAutoClearMessageInputBox();

    return (
        <CheckboxContainer
            label={t("config_page.auto_clear_the_message_box.label")}
            variable={currentEnableAutoClearMessageInputBox}
            toggleFunction={toggleEnableAutoClearMessageInputBox}
        />
    );
};