from customtkinter import CTkFont, CTkFrame, CTkLabel
from utils import callFunctionIfCallable
from ....ui_utils import bindButtonFunctionAndColor

def _createRestartButton(parent_widget, config_window, settings, view_variable, column_num):

    parent_widget.grid_columnconfigure(0, weight=1)
    config_window.restart_button_container = CTkFrame(parent_widget, corner_radius=20, fg_color=settings.ctm.RESTART_BUTTON_BG_COLOR, width=0, height=0, cursor="hand2")
    config_window.restart_button_container.grid(row=0, column=column_num, padx=settings.uism.RESTART_BUTTON_PADX, sticky="ew")


    config_window.restart_button_container.grid_rowconfigure(0, weight=1)
    config_window.restart_button_label = CTkLabel(
        config_window.restart_button_container,
        height=0,
        textvariable=view_variable.VAR_CONFIG_WINDOW_RESTART_BUTTON_LABEL,
        anchor="w",
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.RESTART_BUTTON_LABEL_FONT_SIZE, weight="normal"),
        text_color=settings.ctm.LABELS_TEXT_COLOR
    )
    config_window.restart_button_label.grid(row=0, column=0, padx=20, pady=10)



    bindButtonFunctionAndColor(
        target_widgets=[
            config_window.restart_button_container,
            config_window.restart_button_label,
        ],
        enter_color=settings.ctm.RESTART_BUTTON_HOVERED_BG_COLOR,
        leave_color=settings.ctm.RESTART_BUTTON_BG_COLOR,
        clicked_color=settings.ctm.RESTART_BUTTON_CLICKED_BG_COLOR,
        buttonReleasedFunction=lambda _e: callFunctionIfCallable(view_variable.CALLBACK_RESTART_SOFTWARE),
    )


    config_window.restart_button_container.grid_remove()
