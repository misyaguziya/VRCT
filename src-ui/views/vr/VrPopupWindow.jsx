import { useI18n } from "@useI18n";

import TranslationSvg from "@images/translation.svg?react";
import HmdSvg from "@images/mui_head_mounted_device.svg?react";

import { VrWindow } from "./VrWindow";

// 一時ウィンドウ (言語 / VR設定)。同時に1つだけ開く。中身は後の段階で作る
export const VrPopupWindow = ({ popup, onClose }) => {
    const { t } = useI18n();
    if (popup === "language") {
        return <VrWindow Icon={TranslationSvg} title={t("vr_panel.window_language")} onClose={onClose} />;
    }
    if (popup === "settings") {
        return <VrWindow Icon={HmdSvg} title={t("vr_panel.window_settings")} onClose={onClose} />;
    }
    return null;
};
