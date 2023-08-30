from customtkinter import StringVar
from vrct_gui import vrct_gui

from config import config

def viewInitializer(sidebar_features, language_presets, entry_message_box):

    vrct_gui.CALLBACK_TOGGLE_TRANSLATION = sidebar_features["callback_toggle_translation"],
    vrct_gui.CALLBACK_TOGGLE_TRANSCRIPTION_SEND = sidebar_features["callback_toggle_transcription_send"],
    vrct_gui.CALLBACK_TOGGLE_TRANSCRIPTION_RECEIVE = sidebar_features["callback_toggle_transcription_receive"],
    vrct_gui.CALLBACK_TOGGLE_FOREGROUND = sidebar_features["callback_toggle_foreground"],


    vrct_gui.sqls__optionmenu_your_language.configure(values=language_presets["values"])
    vrct_gui.sqls__optionmenu_your_language.configure(variable=StringVar(value=config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO]))
    vrct_gui.sqls__optionmenu_target_language.configure(values=language_presets["values"])
    vrct_gui.sqls__optionmenu_target_language.configure(variable=StringVar(value=config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]))

    vrct_gui.CALLBACK_SELECTED_TAB_NO_1 = language_presets["callback_selected_tab_no_1"]
    vrct_gui.CALLBACK_SELECTED_TAB_NO_2 = language_presets["callback_selected_tab_no_2"]
    vrct_gui.CALLBACK_SELECTED_TAB_NO_3 = language_presets["callback_selected_tab_no_3"]
    vrct_gui.setDefaultActiveLanguagePresetTab(tab_no=config.SELECTED_TAB_NO)


    def foregroundOffForcefully(e):
        if config.ENABLE_FOREGROUND:
            vrct_gui.attributes("-topmost", False)

    def foregroundOnForcefully(e):
        if config.ENABLE_FOREGROUND:
            vrct_gui.attributes("-topmost", True)


    entry_message_box = getattr(vrct_gui, "entry_message_box")
    entry_message_box.bind("<Return>", lambda: entry_message_box["bind_Return"])
    entry_message_box.bind("<Any-KeyPress>", lambda: entry_message_box["bind_Any_KeyPress"])
    entry_message_box.bind("<FocusIn>", foregroundOffForcefully)
    entry_message_box.bind("<FocusOut>", foregroundOnForcefully)





