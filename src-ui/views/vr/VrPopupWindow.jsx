import { VrLanguageWindow } from "./VrLanguageWindow";
import { VrSettingsWindow } from "./VrSettingsWindow";

// 一時ウィンドウ (言語 / VR設定)。同時に1つだけ開く
export const VrPopupWindow = ({ popup, onClose }) => {
    if (popup === "language") {
        return <VrLanguageWindow onClose={onClose} />;
    }
    if (popup === "settings") {
        return <VrSettingsWindow onClose={onClose} />;
    }
    return null;
};
