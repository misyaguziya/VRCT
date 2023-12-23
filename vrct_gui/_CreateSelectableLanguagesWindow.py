from functools import partial

from .ui_utils import bindButtonReleaseFunction, bindEnterAndLeaveColor, bindButtonPressColor, applyUiScalingAndFixTheBugScrollBar, CustomizedCTkScrollableFrame
from utils import callFunctionIfCallable, makeEven

from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkFont

class _CreateSelectableLanguagesWindow(CTkToplevel):
    def __init__(self, vrct_gui, settings, view_variable):
        super().__init__()
        self.withdraw()

        self.attach = vrct_gui.main_bg_container
        self.vrct_gui = vrct_gui
        self.settings = settings
        self._view_variable = view_variable

        self.is_created = False
        self.selectable_language_window_type = None


        self.title("_CreateSelectableLanguagesWindow")
        self.overrideredirect(True)
        self.configure(fg_color=self.settings.ctm.TOP_BG_COLOR)
        self.protocol("WM_DELETE_WINDOW", vrct_gui._closeSelectableLanguagesWindow)
        self.bind("<FocusOut>", self.focusOutFunction)




    def createContainer(self, selectable_language_window_type):
        self.selectable_language_window_type = selectable_language_window_type

        self.attach.update_idletasks()
        self.x_pos = self.attach.winfo_rootx()
        self.y_pos = self.attach.winfo_rooty()
        self.width_new = makeEven(self.attach.winfo_width())
        self.height_new = makeEven(self.attach.winfo_height())


        self.geometry("{}x{}+{}+{}".format(self.width_new, self.height_new, self.x_pos, self.y_pos))



        if self.is_created is True:
            pass
        else:
            self._createContainer()


    def callbackSelectableLanguages(self, value, _e):
        if self.selectable_language_window_type == "your_language":
            callback = self._view_variable.CALLBACK_SELECTED_YOUR_LANGUAGE
            target_variable = self._view_variable.VAR_YOUR_LANGUAGE
        elif self.selectable_language_window_type == "target_language":
            callback = self._view_variable.CALLBACK_SELECTED_TARGET_LANGUAGE
            target_variable = self._view_variable.VAR_TARGET_LANGUAGE

        target_variable.set(value)
        callFunctionIfCallable(callback, value)
        self.vrct_gui._closeSelectableLanguagesWindow()





    def _createContainer(self):
        self.grid_rowconfigure(0, minsize=self.settings.uism.TOP_BAR_MIN_HEIGHT)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.top_container = CTkFrame(self, corner_radius=0, fg_color=self.settings.ctm.TOP_BG_COLOR, width=0, height=0)
        self.top_container.grid(row=0, column=0, sticky="nsew")


        self.top_container.grid_rowconfigure((0,2), weight=1)
        self.top_container.grid_columnconfigure(1, weight=1)
        self.go_back_button_container = CTkFrame(self.top_container, corner_radius=0, fg_color=self.settings.ctm.GO_BACK_BUTTON_BG_COLOR, width=0, height=0, cursor="hand2")
        self.go_back_button_container.grid(row=1, column=0)

        self.go_back_button_label = CTkLabel(
            self.go_back_button_container,
            textvariable=self._view_variable.VAR_GO_BACK_LABEL_SELECTABLE_LANGUAGE,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.GO_BACK_BUTTON_LABEL_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.BASIC_TEXT_COLOR,
        )
        self.go_back_button_label.grid(row=0, column=0, padx=self.settings.uism.GO_BACK_BUTTON_IPADX, pady=self.settings.uism.GO_BACK_BUTTON_IPADY)


        bindEnterAndLeaveColor([self.go_back_button_container, self.go_back_button_label], self.settings.ctm.GO_BACK_BUTTON_BG_HOVERED_COLOR, self.settings.ctm.GO_BACK_BUTTON_BG_COLOR)
        bindButtonPressColor([self.go_back_button_container, self.go_back_button_label], self.settings.ctm.GO_BACK_BUTTON_BG_CLICKED_COLOR, self.settings.ctm.GO_BACK_BUTTON_BG_COLOR)


        bindButtonReleaseFunction([self.go_back_button_container, self.go_back_button_label], lambda _e: self.vrct_gui._closeSelectableLanguagesWindow())



        self.title_container = CTkFrame(self.top_container, corner_radius=0, fg_color=self.settings.ctm.TOP_BG_COLOR, width=0, height=0)
        self.title_container.grid(row=1, column=1, sticky="nsew")

        self.title_container.grid_columnconfigure((0,2), weight=1)
        self.title_container.grid_rowconfigure((0,2), weight=1)
        self.title_label = CTkLabel(
            self.title_container,
            textvariable=self._view_variable.VAR_TITLE_LABEL_SELECTABLE_LANGUAGE,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.TITLE_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.TITLE_TEXT_COLOR,
        )
        self.title_label.grid(row=1, column=1)




        self.scroll_frame_container = CustomizedCTkScrollableFrame(self, corner_radius=0, fg_color=self.settings.ctm.MAIN_BG_COLOR, width=self.width_new, height=self.height_new)
        self.scroll_frame_container.grid(row=1, column=0, sticky="nsew")

        applyUiScalingAndFixTheBugScrollBar(
            scrollbar_widget=self.scroll_frame_container,
            padx=self.settings.uism.SCROLLBAR_IPADX,
            width=self.settings.uism.SCROLLBAR_WIDTH,
        )


        self.container = CTkFrame(self.scroll_frame_container, corner_radius=0, fg_color=self.settings.ctm.MAIN_BG_COLOR, width=0, height=0)
        self.container.grid(row=0, column=0, sticky="nsew")



        max_row = int(len(self._view_variable.LIST_SELECTABLE_LANGUAGES)/3) + 1
        max_row+=1
        row=0
        column=0
        for selectable_language_name in self._view_variable.LIST_SELECTABLE_LANGUAGES:

            self.wrapper = CTkFrame(self.container, corner_radius=0, fg_color=self.settings.ctm.LANGUAGE_BUTTON_BG_COLOR, width=0, height=0, cursor="hand2")
            self.wrapper.grid(row=row, column=column, sticky="nsew")
            setattr(self, f"{row}_{column}", self.wrapper)



            self.wrapper.grid_rowconfigure((0,2), weight=1)
            selectable_language_name_for_text = selectable_language_name.replace("\n", " ")
            label_widget = CTkLabel(
                self.wrapper,
                text=selectable_language_name_for_text,
                height=0,
                corner_radius=0,
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.VALUES_TEXT_FONT_SIZE, weight="normal"),
                anchor="w",
                text_color=self.settings.ctm.BASIC_TEXT_COLOR,
            )

            label_widget.grid(row=1, column=0, padx=self.settings.uism.VALUES_TEXT_IPADX, pady=self.settings.uism.VALUES_TEXT_IPADY)



            bindEnterAndLeaveColor([self.wrapper, label_widget], self.settings.ctm.LANGUAGE_BUTTON_BG_HOVERED_COLOR, self.settings.ctm.LANGUAGE_BUTTON_BG_COLOR)
            bindButtonPressColor([self.wrapper, label_widget], self.settings.ctm.LANGUAGE_BUTTON_BG_CLICKED_COLOR, self.settings.ctm.LANGUAGE_BUTTON_BG_COLOR)



            callback = partial(self.callbackSelectableLanguages, selectable_language_name)
            bindButtonReleaseFunction([self.wrapper, label_widget], callback)

            if row == max_row:
                row=0
                column+=1
            else:
                row+=1


        self.is_created = True


    def focusOutFunction(self, e):
        if str(e.widget) != ".!_createselectablelanguageswindow":
            return
        self.vrct_gui._closeSelectableLanguagesWindow()