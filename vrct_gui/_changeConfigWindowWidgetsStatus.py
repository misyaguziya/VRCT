from customtkinter import CTkImage

def _changeConfigWindowWidgetsStatus(config_window, settings, view_variable, status, target_names):
    # if target_names == "All":
    #     target_names = []


    def disableLabelsWidgets(target_widget):
        target_widget.label_widget.configure(text_color=settings.ctm.LABELS_TEXT_DISABLED_COLOR)
        if target_widget.desc_widget is not None:
            target_widget.desc_widget.configure(text_color=settings.ctm.LABELS_TEXT_DISABLED_COLOR)

    def normalLabelsWidgets(target_widget):
        target_widget.label_widget.configure(text_color=settings.ctm.LABELS_TEXT_COLOR)
        if target_widget.desc_widget is not None:
            target_widget.desc_widget.configure(text_color=settings.ctm.LABELS_DESC_TEXT_COLOR)


    def disableOptionmenuWidget(target_widget):
        target_widget.optionmenu_label_widget.configure(text_color=settings.ctm.LABELS_TEXT_DISABLED_COLOR)
        target_widget.optionmenu_img_widget.configure(image=CTkImage(settings.image_file.ARROW_LEFT_DISABLED.rotate(90), size=settings.uism.SB__OPTIONMENU_IMG_SIZE))
        target_widget.optionmenu_box.unbindFunction()
        target_widget.optionmenu_box.configure(cursor="")

    def normalOptionmenuWidget(target_widget):
        target_widget.optionmenu_label_widget.configure(text_color=settings.ctm.LABELS_TEXT_COLOR)
        target_widget.optionmenu_img_widget.configure(image=CTkImage(settings.image_file.ARROW_LEFT.rotate(90), size=settings.uism.SB__OPTIONMENU_IMG_SIZE))
        target_widget.optionmenu_box.bindFunction()
        target_widget.optionmenu_box.configure(cursor="hand2")


    for target_name in target_names:
        match target_name:
            case "sb__optionmenu_mic_host":
                if status == "disabled":
                    target_widget = config_window.sb__widgets["sb__optionmenu_mic_host"]
                    disableLabelsWidgets(target_widget)
                    disableOptionmenuWidget(target_widget)

            case "sb__optionmenu_mic_device":
                if status == "disabled":
                    target_widget = config_window.sb__widgets["sb__optionmenu_mic_device"]
                    disableLabelsWidgets(target_widget)
                    disableOptionmenuWidget(target_widget)

            case "sb__optionmenu_appearance_theme":
                if status == "disabled":
                    target_widget = config_window.sb__widgets["sb__optionmenu_appearance_theme"]
                    disableLabelsWidgets(target_widget)
                    disableOptionmenuWidget(target_widget)

            case "sb__optionmenu_ctranslate2_weight_type":
                target_widget = config_window.sb__widgets["sb__optionmenu_ctranslate2_weight_type"]
                if status == "disabled":
                    disableOptionmenuWidget(target_widget)
                elif status == "normal":
                    normalOptionmenuWidget(target_widget)


            case "sb__switch_use_translation_feature":
                target_widget = config_window.sb__widgets["sb__switch_use_translation_feature"]
                if status == "disabled":
                    target_widget.switch_box.configure(
                        state="disabled",
                        fg_color=settings.ctm.SB__SWITCH_BOX_BG_DISABLED_COLOR,
                        progress_color=settings.ctm.SB__SWITCH_BOX_ACTIVE_BG_DISABLED_COLOR,
                        button_color=settings.ctm.SB__SWITCH_BOX_BUTTON_DISABLED_COLOR,
                    )
                elif status == "normal":
                    target_widget.switch_box.configure(
                        state="normal",
                        fg_color=settings.ctm.SB__SWITCH_BOX_BG_COLOR,
                        progress_color=settings.ctm.SB__SWITCH_BOX_ACTIVE_BG_COLOR,
                        button_color=settings.ctm.SB__SWITCH_BOX_BUTTON_COLOR,
                    )

            case "sb__checkbox_enable_send_received_message_to_vrc":
                if status == "disabled":
                    target_widget = config_window.sb__widgets["sb__checkbox_enable_send_received_message_to_vrc"]
                    disableLabelsWidgets(target_widget)
                    target_widget.checkbox.configure(
                        state="disabled",
                        border_color=settings.ctm.SB__CHECKBOX_BORDER_DISABLED_COLOR
                    )

            case _:
                raise ValueError(f"No matching case for target_name: {target_name}")



    config_window.update()