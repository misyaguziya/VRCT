from customtkinter import CTkImage
lock_state_list=[]
def _changeMainWindowWidgetsStatus(vrct_gui, settings, view_variable, status, target_names:list, to_lock_state:bool=False, release_locked_state:bool=False):
    global lock_state_list
    if target_names == "All":
        target_names = ["translation_switch", "transcription_send_switch", "transcription_receive_switch", "foreground_switch", "quick_language_settings", "config_button", "minimize_sidebar_button", "entry_message_box", "send_message_button"]

    if release_locked_state is True:
        for item in target_names:
            if item in lock_state_list:
                lock_state_list.remove(item)

    for item in lock_state_list:
        if item in target_names:
            target_names.remove(item)


    def update_switch_status(
            widget_frame,
            widget_label,
            widget_switch_box,
            widget_selected_mark,
            widget_compact_mode_icon,
            icon_name,
            disabled_icon_name,
        ):

        if status == "disabled":
            widget_frame.configure(cursor="")
            widget_label.configure(text_color=settings.ctm.SF__TEXT_DISABLED_COLOR)
            widget_switch_box.configure(state="disabled", progress_color=settings.ctm.SF__SWITCH_BOX_DISABLE_BG_COLOR, button_color=settings.ctm.SF__SWITCH_BOX_BUTTON_DISABLED_COLOR)
            widget_selected_mark.configure(fg_color=settings.ctm.SF__SELECTED_MARK_DISABLE_BG_COLOR)
            icon_file = disabled_icon_name
        elif status == "normal":
            widget_frame.configure(cursor="hand2")
            widget_label.configure(text_color=settings.ctm.LABELS_TEXT_COLOR)
            widget_switch_box.configure(state="normal", progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_BG_COLOR, button_color=settings.ctm.SF__SWITCH_BOX_BUTTON_COLOR)
            widget_selected_mark.configure(fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_BG_COLOR)
            icon_file = icon_name

        image = CTkImage(icon_file, size=settings.uism.SF__COMPACT_MODE_IMAGE_SIZE)
        widget_compact_mode_icon.configure(image=image)




    for target_name in target_names:
        match target_name:
            case "translation_switch":
                update_switch_status(
                    widget_frame=vrct_gui.translation_frame,
                    widget_label=vrct_gui.label_translation,
                    widget_switch_box=vrct_gui.translation_switch_box,
                    widget_selected_mark=vrct_gui.translation_selected_mark,
                    widget_compact_mode_icon=vrct_gui.translation_compact_mode_icon,
                    icon_name=settings.image_file.TRANSLATION_ICON,
                    disabled_icon_name=settings.image_file.TRANSLATION_ICON_DISABLED
                )
            case "transcription_send_switch":
                update_switch_status(
                    widget_frame=vrct_gui.transcription_send_frame,
                    widget_label=vrct_gui.label_transcription_send,
                    widget_switch_box=vrct_gui.transcription_send_switch_box,
                    widget_selected_mark=vrct_gui.transcription_send_selected_mark,
                    widget_compact_mode_icon=vrct_gui.transcription_send_compact_mode_icon,
                    icon_name=settings.image_file.MIC_ICON,
                    disabled_icon_name=settings.image_file.MIC_ICON_DISABLED
                )
            case "transcription_receive_switch":
                update_switch_status(
                    widget_frame=vrct_gui.transcription_receive_frame,
                    widget_label=vrct_gui.label_transcription_receive,
                    widget_switch_box=vrct_gui.transcription_receive_switch_box,
                    widget_selected_mark=vrct_gui.transcription_receive_selected_mark,
                    widget_compact_mode_icon=vrct_gui.transcription_receive_compact_mode_icon,
                    icon_name=settings.image_file.HEADPHONES_ICON,
                    disabled_icon_name=settings.image_file.HEADPHONES_ICON_DISABLED
                )
            case "foreground_switch":
                update_switch_status(
                    widget_frame=vrct_gui.foreground_frame,
                    widget_label=vrct_gui.label_foreground,
                    widget_switch_box=vrct_gui.foreground_switch_box,
                    widget_selected_mark=vrct_gui.foreground_selected_mark,
                    widget_compact_mode_icon=vrct_gui.foreground_compact_mode_icon,
                    icon_name=settings.image_file.FOREGROUND_ICON,
                    disabled_icon_name=settings.image_file.FOREGROUND_ICON_DISABLED
                )






            case "quick_language_settings":
                if status == "disabled":
                    vrct_gui.sls__container_title.configure(text_color=settings.ctm.SF__TEXT_DISABLED_COLOR)
                    vrct_gui.sls__title_text_your_language.configure(text_color=settings.ctm.SF__TEXT_DISABLED_COLOR)
                    vrct_gui.sls__title_text_target_language.configure(text_color=settings.ctm.SF__TEXT_DISABLED_COLOR)
                    if view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE is False:
                        vrct_gui.current_active_preset_tab.children["!ctklabel"].configure(text_color=settings.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR_PASSIVE)


                elif status == "normal":
                    vrct_gui.sls__container_title.configure(text_color=settings.ctm.LABELS_TEXT_COLOR)
                    vrct_gui.sls__title_text_your_language.configure(text_color=settings.ctm.LABELS_TEXT_COLOR)
                    vrct_gui.sls__title_text_target_language.configure(text_color=settings.ctm.LABELS_TEXT_COLOR)
                    if view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE is False:
                        vrct_gui.current_active_preset_tab.children["!ctklabel"].configure(text_color=settings.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR)
                        vrct_gui.current_active_preset_tab.children["!ctklabel"].configure(text_color=settings.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR)



            case "config_button":
                if status == "disabled":
                    vrct_gui.sidebar_config_button_wrapper.configure(cursor="")
                    vrct_gui.sidebar_config_button.configure(
                        image=CTkImage(settings.image_file.CONFIGURATION_ICON_DISABLED, size=settings.uism.SF__COMPACT_MODE_IMAGE_SIZE),
                    )
                elif status == "normal":
                    vrct_gui.sidebar_config_button_wrapper.configure(cursor="hand2")
                    vrct_gui.sidebar_config_button.configure(
                        image=CTkImage(settings.image_file.CONFIGURATION_ICON, size=settings.uism.SF__COMPACT_MODE_IMAGE_SIZE),
                    )


            case "minimize_sidebar_button":
                MINIMIZE_SIDEBAR_IMAGE_SIZE = vrct_gui.minimize_sidebar_button__for_opening.cget("image").cget("size")
                if status == "disabled":
                    vrct_gui.minimize_sidebar_button_container__for_opening.configure(cursor="")
                    vrct_gui.minimize_sidebar_button_container__for_closing.configure(cursor="")

                    image_file__for_opening = CTkImage((settings.image_file.ARROW_LEFT_DISABLED).rotate(180), size=MINIMIZE_SIDEBAR_IMAGE_SIZE)
                    image_file__for_closing = CTkImage((settings.image_file.ARROW_LEFT_DISABLED), size=MINIMIZE_SIDEBAR_IMAGE_SIZE)

                elif status == "normal":
                    vrct_gui.minimize_sidebar_button_container__for_opening.configure(cursor="hand2")
                    vrct_gui.minimize_sidebar_button_container__for_closing.configure(cursor="hand2")

                    image_file__for_opening = CTkImage((settings.image_file.ARROW_LEFT).rotate(180), size=MINIMIZE_SIDEBAR_IMAGE_SIZE)
                    image_file__for_closing = CTkImage((settings.image_file.ARROW_LEFT), size=MINIMIZE_SIDEBAR_IMAGE_SIZE)
                vrct_gui.minimize_sidebar_button__for_opening.configure(image=image_file__for_opening)
                vrct_gui.minimize_sidebar_button__for_closing.configure(image=image_file__for_closing)


            case "entry_message_box":
                if status == "disabled":
                    vrct_gui.entry_message_box.configure(state="disabled", text_color=settings.ctm.TEXTBOX_ENTRY_TEXT_DISABLED_COLOR)
                    view_variable.IS_ENTRY_MESSAGE_BOX_DISABLED = True
                elif status == "normal":
                    vrct_gui.entry_message_box.configure(state="normal", text_color=settings.ctm.TEXTBOX_ENTRY_TEXT_COLOR)
                    view_variable.IS_ENTRY_MESSAGE_BOX_DISABLED = False


            case "send_message_button":
                if status == "disabled":
                    vrct_gui.main_send_message_button__disabled.grid()
                elif status == "normal":
                    vrct_gui.main_send_message_button__disabled.grid_remove()

            case _:
                raise ValueError(f"No matching case for target_name: {target_name}")


    if to_lock_state is True:
        for item in target_names:
            if item not in lock_state_list:
                lock_state_list.append(item)

    vrct_gui.update()