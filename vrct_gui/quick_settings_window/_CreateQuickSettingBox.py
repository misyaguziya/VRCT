from typing import Union

from utils import callFunctionIfCallable

from customtkinter import CTkImage, CTkLabel, CTkToplevel, CTkProgressBar, CTkFrame, CTkSlider, CTkFont
from ..ui_utils import openImageKeepAspectRatio, getImageFileFromUiUtils, setGeometryToCenterOfScreen, fadeInAnimation

class _CreateQuickSettingBox():
    def __init__(self, parent_frame, vrct_gui, settings, view_variable):
        self.view_variable = view_variable
        self.vrct_gui = vrct_gui
        self.settings = settings
        self.parent_frame = parent_frame









    def _createSettingBoxFrame(self, for_var_label_text=None, for_var_current_value=None):
        setting_box_frame = CTkFrame(self.parent_frame, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)

        setting_box_frame.grid(row=0, column=0, sticky="ew")
        setting_box_frame.grid_columnconfigure(0, weight=1)


        setting_box_frame_wrapper = CTkFrame(setting_box_frame, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        setting_box_frame_wrapper.grid(row=0, column=0, padx=self.settings.uism.SB__IPADX, pady=self.settings.uism.SB__IPADY, sticky="nsew")
        setting_box_frame_wrapper.grid_columnconfigure(0, weight=1)


        # Labels
        setting_box_labels_frame = CTkFrame(setting_box_frame_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        setting_box_labels_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        setting_box_labels_frame.grid_rowconfigure((0,2), weight=1)
        setting_box_labels_frame.grid_columnconfigure(1, weight=1)
        setting_box_label = CTkLabel(
            setting_box_labels_frame,
            textvariable=for_var_label_text,
            anchor="w",
            height=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__LABEL_FONT_SIZE, weight="normal"),
            text_color=self.settings.ctm.LABELS_TEXT_COLOR
        )
        setting_box_label.grid(row=1, column=0, padx=0, pady=0, sticky="nse")



        setting_box_label = CTkLabel(
            setting_box_labels_frame,
            textvariable=for_var_current_value,
            anchor="w",
            height=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__LABEL_FONT_SIZE, weight="normal"),
            text_color=self.settings.ctm.LABELS_TEXT_COLOR
        )
        setting_box_label.grid(row=1, column=2, padx=0, pady=0, sticky="nsw")








        # Items
        setting_box_item_frame = CTkFrame(setting_box_frame_wrapper, corner_radius=0, width=0, height=0, fg_color=self.settings.ctm.SB__BG_COLOR)
        setting_box_item_frame.grid(row=1, column=0, padx=0, sticky="nsew")

        setting_box_item_frame.grid_rowconfigure((0,2), weight=1)
        setting_box_item_frame.grid_columnconfigure(1, weight=1)

        return (setting_box_frame, setting_box_item_frame)
















    def createSettingBoxSlider(
            self,
            for_var_label_text,
            for_var_current_value,
            slider_attr_name,
            slider_range,
            command,
            variable,
            slider_number_of_steps: Union[int,
            None] = None,
            slider_bind__ButtonPress=None,
            slider_bind__ButtonRelease=None,
            sliderTooltipFormatter=None,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(for_var_label_text, for_var_current_value)



        slider_widget = CTkSlider(
            setting_box_item_frame,
            width=self.settings.uism.SB__SLIDER_WIDTH,
            height=self.settings.uism.SB__SLIDER_HEIGHT,
            from_=slider_range[0],
            to=slider_range[1],
            number_of_steps=slider_number_of_steps,
            fg_color=self.settings.ctm.SB__SLIDER_BG_COLOR,
            progress_color=self.settings.ctm.SB__SLIDER_PROGRESS_BG_COLOR,
            button_color=self.settings.ctm.SB__SLIDER_BUTTON_COLOR,
            button_hover_color=self.settings.ctm.SB__SLIDER_BUTTON_HOVERED_COLOR,
            command=command,
            variable=variable,
        )
        setattr(self.vrct_gui, slider_attr_name, slider_widget)


        slider_widget.grid(row=1, column=1, sticky="ew")

        if slider_bind__ButtonPress is not None:
            def adjusted_slider_bind__ButtonPress(e):
                command(e)
                slider_bind__ButtonPress()
            slider_widget.configure(command=adjusted_slider_bind__ButtonPress)

        if slider_bind__ButtonRelease is not None:
            def adjusted_slider_bind__ButtonRelease(_e):
                slider_bind__ButtonRelease()
            slider_widget.bind("<ButtonRelease>", adjusted_slider_bind__ButtonRelease, "+")

        return setting_box_frame