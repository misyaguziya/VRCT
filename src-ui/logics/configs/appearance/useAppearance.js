import {
    useStore_UiLanguage,
    useStore_UiScaling,
    useStore_MessageLogUiScaling,
    useStore_SendMessageButtonType,
    useStore_ShowResendButton,
    useStore_SelectedFontFamily,
    useStore_Transparency,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useAppearance = () => {
    const { asyncStdoutToPython } = useStdoutToPython();

    // UI Language
    const { currentUiLanguage, updateUiLanguage, pendingUiLanguage } = useStore_UiLanguage();
    // UI Scaling
    const { currentUiScaling, updateUiScaling, pendingUiScaling } = useStore_UiScaling();
    // Message Log Ui Scaling
    const { currentMessageLogUiScaling, updateMessageLogUiScaling, pendingMessageLogUiScaling } = useStore_MessageLogUiScaling();
    // Send Message Button Type
    const { currentSendMessageButtonType, updateSendMessageButtonType, pendingSendMessageButtonType } = useStore_SendMessageButtonType();
    // Show Resend Button
    const { currentShowResendButton, updateShowResendButton, pendingShowResendButton } = useStore_ShowResendButton();
    // Selected Font Family
    const { currentSelectedFontFamily, updateSelectedFontFamily, pendingSelectedFontFamily } = useStore_SelectedFontFamily();
    // Transparency
    const { currentTransparency, updateTransparency, pendingTransparency } = useStore_Transparency();


    // UI Language
    const getUiLanguage = () => {
        pendingUiLanguage();
        asyncStdoutToPython("/get/data/ui_language");
    };

    const setUiLanguage = (selected_ui_language) => {
        pendingUiLanguage();
        asyncStdoutToPython("/set/data/ui_language", selected_ui_language);
    };

    // UI Scaling
    const getUiScaling = () => {
        pendingUiScaling();
        asyncStdoutToPython("/get/data/ui_scaling");
    };

    const setUiScaling = (selected_ui_scaling) => {
        pendingUiScaling();
        asyncStdoutToPython("/set/data/ui_scaling", selected_ui_scaling);
    };

    // Message Log Ui Scaling
    const getMessageLogUiScaling = () => {
        pendingMessageLogUiScaling();
        asyncStdoutToPython("/get/data/textbox_ui_scaling");
    };

    const setMessageLogUiScaling = (selected_ui_scaling) => {
        pendingMessageLogUiScaling();
        asyncStdoutToPython("/set/data/textbox_ui_scaling", selected_ui_scaling);
    };

    // Send Message Button Type
    const getSendMessageButtonType = () => {
        pendingSendMessageButtonType();
        asyncStdoutToPython("/get/data/send_message_button_type");
    };

    const setSendMessageButtonType = (send_message_button_type) => {
        pendingSendMessageButtonType();
        asyncStdoutToPython("/set/data/send_message_button_type", send_message_button_type);
    };

    // Show Resend Button
    const getShowResendButton = () => {
        pendingShowResendButton();
        asyncStdoutToPython("/get/data/show_resend_button");
    };

    const toggleShowResendButton = () => {
        pendingShowResendButton();
        if (currentShowResendButton.data) {
            asyncStdoutToPython("/set/disable/show_resend_button");
        } else {
            asyncStdoutToPython("/set/enable/show_resend_button");
        }
    };

    // Selected Font Family
    const getSelectedFontFamily = () => {
        pendingSelectedFontFamily();
        asyncStdoutToPython("/get/data/font_family");
    };

    const setSelectedFontFamily = (selected_font_family) => {
        pendingSelectedFontFamily();
        asyncStdoutToPython("/set/data/font_family", selected_font_family);
    };

    // Transparency
    const getTransparency = () => {
        pendingTransparency();
        asyncStdoutToPython("/get/data/transparency");
    };

    const setTransparency = (selected_transparency) => {
        pendingTransparency();
        asyncStdoutToPython("/set/data/transparency", selected_transparency);
    };


    return {
        // UI Language
        currentUiLanguage,
        getUiLanguage,
        updateUiLanguage,
        setUiLanguage,

        // UI Scaling
        currentUiScaling,
        getUiScaling,
        updateUiScaling,
        setUiScaling,

        // Message Log Ui Scaling
        currentMessageLogUiScaling,
        getMessageLogUiScaling,
        updateMessageLogUiScaling,
        setMessageLogUiScaling,

        // Send Message Button Type
        currentSendMessageButtonType,
        getSendMessageButtonType,
        setSendMessageButtonType,
        updateSendMessageButtonType,

        // Show Resend Button
        currentShowResendButton,
        getShowResendButton,
        updateShowResendButton,
        toggleShowResendButton,

        // Selected Font Family
        currentSelectedFontFamily,
        getSelectedFontFamily,
        updateSelectedFontFamily,
        setSelectedFontFamily,

        // Transparency
        currentTransparency,
        getTransparency,
        updateTransparency,
        setTransparency,
    };
};