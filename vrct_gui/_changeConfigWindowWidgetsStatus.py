from customtkinter import CTkImage

def _changeConfigWindowWidgetsStatus(config_window, settings, view_variable, status, target_names):
    if target_names == "All":
        target_names = ["mic_energy_threshold_check_button", "speaker_energy_threshold_check_button"]


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


            case _:
                raise ValueError(f"No matching case for target_name: {target_name}")



    config_window.update()