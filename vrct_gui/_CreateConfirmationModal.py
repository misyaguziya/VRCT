from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkFont

from .ui_utils import fadeInAnimation, setGeometryToCenterOfTheWidget, bindButtonFunctionAndColor

from utils import callFunctionIfCallable

class _CreateConfirmationModal(CTkToplevel):
    def __init__(self, attach_window, settings, view_variable, modal_type=None):
        super().__init__()
        self.withdraw()

        self.attach_window = attach_window
        self.settings = settings
        self._view_variable = view_variable


        self.title("")
        self.overrideredirect(True)
        self.wm_attributes("-toolwindow", True)

        self.BIND_FOCUS_OUT_FUNC_ID=None



        self.configure(fg_color=self.settings.ctm.FAKE_BORDER_COLOR)
        self.protocol("WM_DELETE_WINDOW", lambda: callFunctionIfCallable(self._view_variable.CALLBACK_HIDE_CONFIRMATION_MODAL))



        self.grid_rowconfigure(0,weight=1)
        self.grid_columnconfigure(0,weight=1)
        self.modal_container = CTkFrame(self, corner_radius=0, fg_color=self.settings.ctm.BG_COLOR)
        self.modal_container.grid(row=0, column=0, padx=self.settings.uism.FAKE_BORDER_SIZE, pady=self.settings.uism.FAKE_BORDER_SIZE)


        self.modal_contents_wrapper = CTkFrame(self.modal_container, corner_radius=0, fg_color=self.settings.ctm.BG_COLOR)
        self.modal_contents_wrapper.grid(row=0, column=0, padx=self.settings.uism.CONTENTS_WRAPPER, pady=self.settings.uism.CONTENTS_WRAPPER)



        self.modal_contents_wrapper.grid_rowconfigure(1, minsize=self.settings.uism.MARGIN_BETWEEN_MESSAGE_AND_BUTTONS)

        self.modal_message_label_wrapper = CTkFrame(self.modal_contents_wrapper, corner_radius=0, fg_color=self.settings.ctm.BG_COLOR)
        self.modal_message_label_wrapper.grid(row=0, column=0)

        self.modal_message_label_wrapper.grid_rowconfigure((0,2),weight=1)
        self.modal_message_label_wrapper.grid_columnconfigure((0,2),weight=1)

        self.modal_message_label = CTkLabel(
            self.modal_message_label_wrapper,
            textvariable=self._view_variable.VAR_MESSAGE_CONFIRMATION_MODAL,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.MESSAGE_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.MESSAGE_TEXT_COLOR,
        )
        self.modal_message_label.grid(row=1, column=1)



        self.modal_buttons_container = CTkFrame(self.modal_contents_wrapper, corner_radius=0, fg_color=self.settings.ctm.BG_COLOR)
        self.modal_buttons_container.grid(row=2, column=0, sticky="nsew")

        self.modal_buttons_container.grid_rowconfigure((0,2),weight=1)
        self.modal_buttons_container.grid_columnconfigure(0,weight=1)

        self.modal_buttons_wrapper = CTkFrame(self.modal_buttons_container, corner_radius=0, fg_color=self.settings.ctm.BG_COLOR)
        self.modal_buttons_wrapper.grid(row=1, column=0, sticky="ew")


        if modal_type == "information":
            self.modal_buttons_wrapper.grid_columnconfigure((0,2), weight=1)


            self.accept_button = CTkFrame(self.modal_buttons_wrapper, corner_radius=self.settings.uism.BUTTONS_CORNER_RADIUS, fg_color=self.settings.ctm.ACCEPT_BUTTON_BG_COLOR, cursor="hand2")
            self.accept_button.grid(row=0, column=1, sticky="ew")


            self.accept_button.grid_columnconfigure(0, weight=1)
            self.accept_button_label_wrapper = CTkFrame(self.accept_button, corner_radius=0, fg_color=self.settings.ctm.ACCEPT_BUTTON_BG_COLOR)
            self.accept_button_label_wrapper.grid(row=0, column=0, padx=self.settings.uism.BUTTONS_IPADX, pady=self.settings.uism.BUTTONS_IPADY, sticky="ew")

            self.accept_button_label_wrapper.grid_columnconfigure((0,2), weight=1)
            self.accept_button_label = CTkLabel(
                self.accept_button_label_wrapper,
                textvariable=self._view_variable.VAR_LABEL_CONFIRMATION_MODAL_ACCEPT_BUTTON,
                height=0,
                corner_radius=0,
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.CONFIRMATION_BUTTONS_TEXT_FONT_SIZE, weight="normal"),
                anchor="w",
                text_color=self.settings.ctm.CONFIRMATION_BUTTONS_TEXT_COLOR,
            )
            self.accept_button_label.grid(row=0, column=1)



            bindButtonFunctionAndColor(
                target_widgets=[
                    self.accept_button,
                    self.accept_button_label_wrapper,
                    self.accept_button_label,
                ],
                enter_color=settings.ctm.ACCEPT_BUTTON_HOVERED_BG_COLOR,
                leave_color=settings.ctm.ACCEPT_BUTTON_BG_COLOR,
                clicked_color=settings.ctm.ACCEPT_BUTTON_CLICKED_BG_COLOR,
                buttonReleasedFunction=lambda _e: callFunctionIfCallable(self._view_variable.CALLBACK_ACCEPTED_CONFIRMATION_MODAL),
            )






        else:
            self.modal_buttons_wrapper.grid_columnconfigure(1, weight=1, minsize=self.settings.uism.BUTTONS_BETWEEN_PADDING)
            self.modal_buttons_wrapper.grid_columnconfigure((0,2), weight=0, uniform="button_wrapper")





            self.deny_button = CTkFrame(self.modal_buttons_wrapper, corner_radius=self.settings.uism.BUTTONS_CORNER_RADIUS, fg_color=self.settings.ctm.DENY_BUTTON_BG_COLOR, cursor="hand2")
            self.deny_button.grid(row=0, column=0, sticky="ew")


            self.deny_button.grid_columnconfigure(0, weight=1)
            self.deny_button_label_wrapper = CTkFrame(self.deny_button, corner_radius=0, fg_color=self.settings.ctm.DENY_BUTTON_BG_COLOR)
            self.deny_button_label_wrapper.grid(row=0, column=0, padx=self.settings.uism.BUTTONS_IPADX, pady=self.settings.uism.BUTTONS_IPADY, sticky="ew")

            self.deny_button_label_wrapper.grid_columnconfigure((0,2), weight=1)


            self.deny_button_label_wrapper.grid_columnconfigure(0, weight=1)
            self.deny_button_label = CTkLabel(
                self.deny_button_label_wrapper,
                textvariable=self._view_variable.VAR_LABEL_CONFIRMATION_MODAL_DENY_BUTTON,
                height=0,
                corner_radius=0,
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.CONFIRMATION_BUTTONS_TEXT_FONT_SIZE, weight="normal"),
                anchor="w",
                text_color=self.settings.ctm.CONFIRMATION_BUTTONS_TEXT_COLOR,
            )
            self.deny_button_label.grid(row=0, column=1)



            bindButtonFunctionAndColor(
                target_widgets=[
                    self.deny_button,
                    self.deny_button_label_wrapper,
                    self.deny_button_label,
                ],
                enter_color=settings.ctm.DENY_BUTTON_HOVERED_BG_COLOR,
                leave_color=settings.ctm.DENY_BUTTON_BG_COLOR,
                clicked_color=settings.ctm.DENY_BUTTON_CLICKED_BG_COLOR,
                buttonReleasedFunction=lambda _e: callFunctionIfCallable(self._view_variable.CALLBACK_DENIED_CONFIRMATION_MODAL),
            )



            self.accept_button = CTkFrame(self.modal_buttons_wrapper, corner_radius=self.settings.uism.BUTTONS_CORNER_RADIUS, fg_color=self.settings.ctm.ACCEPT_BUTTON_BG_COLOR, cursor="hand2")
            self.accept_button.grid(row=0, column=2, sticky="ew")


            self.accept_button.grid_columnconfigure(0, weight=1)
            self.accept_button_label_wrapper = CTkFrame(self.accept_button, corner_radius=0, fg_color=self.settings.ctm.ACCEPT_BUTTON_BG_COLOR)
            self.accept_button_label_wrapper.grid(row=0, column=0, padx=self.settings.uism.BUTTONS_IPADX, pady=self.settings.uism.BUTTONS_IPADY, sticky="ew")

            self.accept_button_label_wrapper.grid_columnconfigure((0,2), weight=1)
            self.accept_button_label = CTkLabel(
                self.accept_button_label_wrapper,
                textvariable=self._view_variable.VAR_LABEL_CONFIRMATION_MODAL_ACCEPT_BUTTON,
                height=0,
                corner_radius=0,
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.CONFIRMATION_BUTTONS_TEXT_FONT_SIZE, weight="normal"),
                anchor="w",
                text_color=self.settings.ctm.CONFIRMATION_BUTTONS_TEXT_COLOR,
            )
            self.accept_button_label.grid(row=0, column=1)



            bindButtonFunctionAndColor(
                target_widgets=[
                    self.accept_button,
                    self.accept_button_label_wrapper,
                    self.accept_button_label,
                ],
                enter_color=settings.ctm.ACCEPT_BUTTON_HOVERED_BG_COLOR,
                leave_color=settings.ctm.ACCEPT_BUTTON_BG_COLOR,
                clicked_color=settings.ctm.ACCEPT_BUTTON_CLICKED_BG_COLOR,
                buttonReleasedFunction=lambda _e: callFunctionIfCallable(self._view_variable.CALLBACK_ACCEPTED_CONFIRMATION_MODAL),
            )



    def hide_buttons(self):
        self.modal_buttons_wrapper.grid_remove()


    def show(self, hide_title_bar:bool=True, close_when_focusout:bool=True):
        self.modal_buttons_wrapper.grid()

        if hide_title_bar is False:
            self.overrideredirect(False)
        else:
            self.overrideredirect(True)

        self.close_when_focusout = close_when_focusout
        if self.close_when_focusout is True:
            self.BIND_FOCUS_OUT_FUNC_ID = self.bind("<FocusOut>", self.focusOutFunction, "+")
        else:
            self._grab_set()


        self.attributes("-alpha", 0)
        self.deiconify()
        setGeometryToCenterOfTheWidget(
            attach_widget=self.attach_window,
            target_widget=self
        )
        fadeInAnimation(self, steps=5, interval=0.005, max_alpha=1)
        self.lift()
        self.focus_set()


    def hide(self):
        if self.BIND_FOCUS_OUT_FUNC_ID is not None:
            self.unbind("<FocusOut>", self.BIND_FOCUS_OUT_FUNC_ID)

        self.withdraw()
        self.grab_release()

    def focusOutFunction(self, e):
        if str(e.widget) != ".!_createconfirmationmodal":
            return
        callFunctionIfCallable(self._view_variable.CALLBACK_HIDE_CONFIRMATION_MODAL)

    def _grab_set(self):
        self.grab_set()
