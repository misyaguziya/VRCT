from customtkinter import CTkImage

from .ui_utils import getImageFileFromUiUtils


def _changeMainWindowWidgetsStatus(vrct_gui, settings, status, target_names):
    COMPACT_MODE_ICON_SIZE_TUPLES = (settings.COMPACT_MODE_ICON_SIZE, settings.COMPACT_MODE_ICON_SIZE)

    if target_names == "All":
        target_names = ["translation_switch", "transcription_send_switch", "transcription_receive_switch", "foreground_switch", "quick_language_settings", "config_button", "minimize_sidebar_button", "entry_message_box"]




    def update_switch_status(widget_frame, widget_label, widget_switch_box, widget_selected_mark, widget_compact_mode_icon, icon_name, disabled_icon_name):
        if status == "disabled":
            widget_frame.configure(cursor="")
            widget_label.configure(text_color=settings.ctm.SF__TEXT_DISABLED_COLOR)
            widget_switch_box.configure(state="disabled", progress_color=settings.ctm.SF__SWITCH_BOX_DISABLE_BG_COLOR)
            widget_selected_mark.configure(fg_color=settings.ctm.SF__SELECTED_MARK_DISABLE_BG_COLOR)
            icon_filename = disabled_icon_name
        elif status == "normal":
            widget_frame.configure(cursor="hand2")
            widget_label.configure(text_color=settings.ctm.LABELS_TEXT_COLOR)
            widget_switch_box.configure(state="normal", progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_BG_COLOR)
            widget_selected_mark.configure(fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_BG_COLOR)
            icon_filename = icon_name

        image = CTkImage(getImageFileFromUiUtils(icon_filename), size=COMPACT_MODE_ICON_SIZE_TUPLES)
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
                    icon_name=settings.image_filename.TRANSLATION_ICON,
                    disabled_icon_name=settings.image_filename.TRANSLATION_ICON_DISABLED
                )
            case "transcription_send_switch":
                update_switch_status(
                    widget_frame=vrct_gui.transcription_send_frame,
                    widget_label=vrct_gui.label_transcription_send,
                    widget_switch_box=vrct_gui.transcription_send_switch_box,
                    widget_selected_mark=vrct_gui.transcription_send_selected_mark,
                    widget_compact_mode_icon=vrct_gui.transcription_send_compact_mode_icon,
                    icon_name=settings.image_filename.MIC_ICON,
                    disabled_icon_name=settings.image_filename.MIC_ICON_DISABLED
                )
            case "transcription_receive_switch":
                update_switch_status(
                    widget_frame=vrct_gui.transcription_receive_frame,
                    widget_label=vrct_gui.label_transcription_receive,
                    widget_switch_box=vrct_gui.transcription_receive_switch_box,
                    widget_selected_mark=vrct_gui.transcription_receive_selected_mark,
                    widget_compact_mode_icon=vrct_gui.transcription_receive_compact_mode_icon,
                    icon_name=settings.image_filename.HEADPHONES_ICON,
                    disabled_icon_name=settings.image_filename.HEADPHONES_ICON_DISABLED
                )
            case "foreground_switch":
                update_switch_status(
                    widget_frame=vrct_gui.foreground_frame,
                    widget_label=vrct_gui.label_foreground,
                    widget_switch_box=vrct_gui.foreground_switch_box,
                    widget_selected_mark=vrct_gui.foreground_selected_mark,
                    widget_compact_mode_icon=vrct_gui.foreground_compact_mode_icon,
                    icon_name=settings.image_filename.FOREGROUND_ICON,
                    disabled_icon_name=settings.image_filename.FOREGROUND_ICON_DISABLED
                )






            case "quick_language_settings":
                if status == "disabled":
                    vrct_gui.sqls__container_title.configure(text_color=settings.ctm.SF__TEXT_DISABLED_COLOR)
                    vrct_gui.sqls__title_text_your_language.configure(text_color=settings.ctm.SF__TEXT_DISABLED_COLOR)
                    vrct_gui.sqls__title_text_target_language.configure(text_color=settings.ctm.SF__TEXT_DISABLED_COLOR)
                    if settings.IS_SIDEBAR_COMPACT_MODE is False:
                        vrct_gui.current_active_preset_tab.children["!ctklabel"].configure(text_color=settings.ctm.SQLS__PRESETS_TAB_ACTIVE_TEXT_COLOR_PASSIVE)
                    vrct_gui.sqls__optionmenu_your_language.configure(state="disabled")
                    vrct_gui.sqls__optionmenu_target_language.configure(state="disabled")

                elif status == "normal":
                    vrct_gui.sqls__container_title.configure(text_color=settings.ctm.LABELS_TEXT_COLOR)
                    vrct_gui.sqls__title_text_your_language.configure(text_color=settings.ctm.LABELS_TEXT_COLOR)
                    vrct_gui.sqls__title_text_target_language.configure(text_color=settings.ctm.LABELS_TEXT_COLOR)
                    if settings.IS_SIDEBAR_COMPACT_MODE is False:
                        vrct_gui.current_active_preset_tab.children["!ctklabel"].configure(text_color=settings.ctm.SQLS__PRESETS_TAB_ACTIVE_TEXT_COLOR)
                        vrct_gui.current_active_preset_tab.children["!ctklabel"].configure(text_color=settings.ctm.SQLS__PRESETS_TAB_ACTIVE_TEXT_COLOR)
                    vrct_gui.sqls__optionmenu_your_language.configure(state="normal")
                    vrct_gui.sqls__optionmenu_target_language.configure(state="normal")


            case "config_button":
                if status == "disabled":
                    vrct_gui.sidebar_config_button_wrapper.configure(cursor="")
                    vrct_gui.sidebar_config_button.configure(
                        image=CTkImage(getImageFileFromUiUtils(settings.image_filename.CONFIGURATION_ICON_DISABLED)),
                    )
                elif status == "normal":
                    vrct_gui.sidebar_config_button_wrapper.configure(cursor="hand2")
                    vrct_gui.sidebar_config_button.configure(
                        image=CTkImage(getImageFileFromUiUtils(settings.image_filename.CONFIGURATION_ICON)),
                    )


            case "minimize_sidebar_button":
                LOGO_SIZE = vrct_gui.minimize_sidebar_button.cget("image").cget("size")
                if status == "disabled":
                    vrct_gui.minimize_sidebar_button_container.configure(cursor="")


                    if settings.IS_SIDEBAR_COMPACT_MODE is True:
                        image_file = CTkImage(getImageFileFromUiUtils(settings.image_filename.ARROW_LEFT_DISABLED).rotate(180), size=LOGO_SIZE)
                    else:
                        image_file = CTkImage(getImageFileFromUiUtils(settings.image_filename.ARROW_LEFT_DISABLED), size=LOGO_SIZE)
                    vrct_gui.minimize_sidebar_button.configure(image=image_file)

                elif status == "normal":
                    vrct_gui.minimize_sidebar_button_container.configure(cursor="hand2")
                    if settings.IS_SIDEBAR_COMPACT_MODE is True:
                        image_file = CTkImage(getImageFileFromUiUtils(settings.image_filename.ARROW_LEFT).rotate(180), size=LOGO_SIZE)
                    else:
                        image_file = CTkImage(getImageFileFromUiUtils(settings.image_filename.ARROW_LEFT), size=LOGO_SIZE)
                    vrct_gui.minimize_sidebar_button.configure(image=image_file)


            case "entry_message_box":
                if status == "disabled":
                    vrct_gui.entry_message_box.configure(state="disabled", placeholder_text_color=settings.ctm.TEXTBOX_ENTRY_PLACEHOLDER_DISABLED_COLOR, text_color=settings.ctm.TEXTBOX_ENTRY_TEXT_DISABLED_COLOR)
                elif status == "normal":
                    vrct_gui.entry_message_box.configure(state="normal", placeholder_text_color=settings.ctm.TEXTBOX_ENTRY_PLACEHOLDER_COLOR, text_color=settings.ctm.TEXTBOX_ENTRY_TEXT_COLOR)


            case _:
                raise ValueError(f"No matching case for target_name: {target_name}")



    vrct_gui.update()