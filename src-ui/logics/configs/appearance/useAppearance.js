import { useAppearance_S } from "../../../ui_config_setter";

export const useAppearance = () => {
    return {...useAppearance_S()};
}

// import {
//     useStore_UiLanguage,
//     useStore_UiScaling,
//     useStore_MessageLogUiScaling,
//     useStore_SendMessageButtonType,
//     useStore_ShowResendButton,
//     useStore_SelectedFontFamily,
//     useStore_Transparency,
// } from "@store";
// import { useStdoutToPython } from "@useStdoutToPython";
// import { useI18n } from "@useI18n";
// import { useNotificationStatus } from "@logics_common";

// export const useAppearance = () => {
//     const { t } = useI18n();
//     const { asyncStdoutToPython } = useStdoutToPython();
//     const { showNotification_SaveSuccess } = useNotificationStatus();

//     // UI Language
//     const { currentUiLanguage, updateUiLanguage, pendingUiLanguage } = useStore_UiLanguage();
//     // UI Scaling
//     const { currentUiScaling, updateUiScaling, pendingUiScaling } = useStore_UiScaling();
//     // Message Log Ui Scaling
//     const { currentMessageLogUiScaling, updateMessageLogUiScaling, pendingMessageLogUiScaling } = useStore_MessageLogUiScaling();
//     // Send Message Button Type
//     const { currentSendMessageButtonType, updateSendMessageButtonType, pendingSendMessageButtonType } = useStore_SendMessageButtonType();
//     // Show Resend Button
//     const { currentShowResendButton, updateShowResendButton, pendingShowResendButton } = useStore_ShowResendButton();
//     // Selected Font Family
//     const { currentSelectedFontFamily, updateSelectedFontFamily, pendingSelectedFontFamily } = useStore_SelectedFontFamily();
//     // Transparency
//     const { currentTransparency, updateTransparency, pendingTransparency } = useStore_Transparency();


//     // UI Language
//     const getUiLanguage = () => {
//         pendingUiLanguage();
//         asyncStdoutToPython("/get/data/ui_language");
//     };

//     const setUiLanguage = (selected_ui_language) => {
//         pendingUiLanguage();
//         asyncStdoutToPython("/set/data/ui_language", selected_ui_language);
//     };

//     const setSuccessUiLanguage = (selected_ui_language) => {
//         updateUiLanguage(selected_ui_language);
//         showNotification_SaveSuccess();
//     };

//     // UI Scaling
//     const getUiScaling = () => {
//         pendingUiScaling();
//         asyncStdoutToPython("/get/data/ui_scaling");
//     };

//     const setUiScaling = (selected_ui_scaling) => {
//         pendingUiScaling();
//         asyncStdoutToPython("/set/data/ui_scaling", selected_ui_scaling);
//     };

//     const setSuccessUiScaling = (selected_ui_scaling) => {
//         updateUiScaling(selected_ui_scaling);
//         showNotification_SaveSuccess();
//     };

//     // Message Log Ui Scaling
//     const getMessageLogUiScaling = () => {
//         pendingMessageLogUiScaling();
//         asyncStdoutToPython("/get/data/textbox_ui_scaling");
//     };

//     const setMessageLogUiScaling = (selected_ui_scaling) => {
//         pendingMessageLogUiScaling();
//         asyncStdoutToPython("/set/data/textbox_ui_scaling", selected_ui_scaling);
//     };

//     const setSuccessMessageLogUiScaling = (selected_ui_scaling) => {
//         updateMessageLogUiScaling(selected_ui_scaling);
//         showNotification_SaveSuccess();
//     };

//     // Send Message Button Type
//     const getSendMessageButtonType = () => {
//         pendingSendMessageButtonType();
//         asyncStdoutToPython("/get/data/send_message_button_type");
//     };

//     const setSendMessageButtonType = (send_message_button_type) => {
//         pendingSendMessageButtonType();
//         asyncStdoutToPython("/set/data/send_message_button_type", send_message_button_type);
//     };

//     const setSuccessSendMessageButtonType = (send_message_button_type) => {
//         updateSendMessageButtonType(send_message_button_type);
//         showNotification_SaveSuccess();
//     };

//     // Show Resend Button
//     const getShowResendButton = () => {
//         pendingShowResendButton();
//         asyncStdoutToPython("/get/data/show_resend_button");
//     };

//     const toggleShowResendButton = () => {
//         pendingShowResendButton();
//         if (currentShowResendButton.data) {
//             asyncStdoutToPython("/set/disable/show_resend_button");
//         } else {
//             asyncStdoutToPython("/set/enable/show_resend_button");
//         }
//     };
//     const setSuccessShowResendButton = (to_show) => {
//         updateShowResendButton(to_show);
//         showNotification_SaveSuccess();
//     };

//     // Selected Font Family
//     const getSelectedFontFamily = () => {
//         pendingSelectedFontFamily();
//         asyncStdoutToPython("/get/data/font_family");
//     };

//     const setSelectedFontFamily = (selected_font_family) => {
//         pendingSelectedFontFamily();
//         asyncStdoutToPython("/set/data/font_family", selected_font_family);
//     };

//     const setSuccessSelectedFontFamily = (selected_font_family) => {
//         updateSelectedFontFamily(selected_font_family);
//         showNotification_SaveSuccess();
//     };

//     // Transparency
//     const getTransparency = () => {
//         pendingTransparency();
//         asyncStdoutToPython("/get/data/transparency");
//     };

//     const setTransparency = (selected_transparency) => {
//         pendingTransparency();
//         asyncStdoutToPython("/set/data/transparency", selected_transparency);
//     };

//     const setSuccessTransparency = (selected_transparency) => {
//         updateTransparency(selected_transparency);
//         showNotification_SaveSuccess();
//     };


//     return {
//         // UI Language
//         currentUiLanguage,
//         getUiLanguage,
//         updateUiLanguage,
//         setUiLanguage,
//         setSuccessUiLanguage,

//         // UI Scaling
//         currentUiScaling,
//         getUiScaling,
//         updateUiScaling,
//         setUiScaling,
//         setSuccessUiScaling,

//         // Message Log Ui Scaling
//         currentMessageLogUiScaling,
//         getMessageLogUiScaling,
//         updateMessageLogUiScaling,
//         setMessageLogUiScaling,
//         setSuccessMessageLogUiScaling,

//         // Send Message Button Type
//         currentSendMessageButtonType,
//         getSendMessageButtonType,
//         setSendMessageButtonType,
//         setSuccessSendMessageButtonType,
//         updateSendMessageButtonType,

//         // Show Resend Button
//         currentShowResendButton,
//         getShowResendButton,
//         updateShowResendButton,
//         toggleShowResendButton,
//         setSuccessShowResendButton,

//         // Selected Font Family
//         currentSelectedFontFamily,
//         getSelectedFontFamily,
//         updateSelectedFontFamily,
//         setSelectedFontFamily,
//         setSuccessSelectedFontFamily,

//         // Transparency
//         currentTransparency,
//         getTransparency,
//         updateTransparency,
//         setTransparency,
//         setSuccessTransparency,
//     };
// };