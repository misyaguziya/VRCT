from customtkinter import CTkImage

def _changeConfigWindowWidgetsStatus(config_window, settings, view_variable, status, target_names):
    if target_names == "All":
        target_names = ["mic_energy_threshold_check_button", "speaker_energy_threshold_check_button"]


    def disableOptionmenuWidget(target_widget):
        target_widget.label_widget.configure(text_color=settings.ctm.LABELS_TEXT_DISABLED_COLOR)
        if target_widget.desc_widget is not None:
            target_widget.desc_widget.configure(text_color=settings.ctm.LABELS_TEXT_DISABLED_COLOR)
        target_widget.optionmenu_label_widget.configure(text_color=settings.ctm.LABELS_TEXT_DISABLED_COLOR)
        target_widget.optionmenu_img_widget.configure(image=CTkImage(settings.image_file.ARROW_LEFT_DISABLED.rotate(90), size=settings.uism.SB__OPTIONMENU_IMG_SIZE))
        target_widget.optionmenu_box.unbindFunction()
        target_widget.optionmenu_box.configure(cursor="")


    for target_name in target_names:
        match target_name:
            case "mic_energy_threshold_check_button":
                if status == "disabled":
                    config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold.configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR)
                    config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold.children["!ctklabel"].configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR)

                elif status == "normal":
                    config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold.configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_COLOR)
                    config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold.children["!ctklabel"].configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_COLOR)

            case "speaker_energy_threshold_check_button":
                if status == "disabled":
                    config_window.sb__progressbar_x_slider__passive_button_speaker_energy_threshold.configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR)
                    config_window.sb__progressbar_x_slider__passive_button_speaker_energy_threshold.children["!ctklabel"].configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR)

                elif status == "normal":
                    config_window.sb__progressbar_x_slider__passive_button_speaker_energy_threshold.configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_COLOR)
                    config_window.sb__progressbar_x_slider__passive_button_speaker_energy_threshold.children["!ctklabel"].configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_COLOR)


            case "sb__optionmenu_mic_host":
                if status == "disabled":
                    target_widget = config_window.sb__widgets["sb__optionmenu_mic_host"]
                    disableOptionmenuWidget(target_widget)

            case "sb__optionmenu_mic_device":
                if status == "disabled":
                    target_widget = config_window.sb__widgets["sb__optionmenu_mic_device"]
                    disableOptionmenuWidget(target_widget)

            case "sb__optionmenu_speaker_device":
                if status == "disabled":
                    target_widget = config_window.sb__widgets["sb__optionmenu_speaker_device"]
                    disableOptionmenuWidget(target_widget)


            case _:
                raise ValueError(f"No matching case for target_name: {target_name}")



    config_window.update()