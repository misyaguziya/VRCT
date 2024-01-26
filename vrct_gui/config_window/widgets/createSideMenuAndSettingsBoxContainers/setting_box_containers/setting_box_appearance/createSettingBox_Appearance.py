from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Appearance(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxDropdownMenu = sbg.createSettingBoxDropdownMenu
    createSettingBoxSlider = sbg.createSettingBoxSlider
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox


    def sliderTransparencyCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_TRANSPARENCY, value)

    def optionmenuAppearanceThemeCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_APPEARANCE, value)

    def optionmenuUiScalingCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_UI_SCALING, value)

    def sliderTextBoxUiScalingCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_TEXTBOX_UI_SCALING, value)

    def sliderMessageBoxRatioCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MESSAGE_BOX_RATIO, value)

    def optionmenuFontFamilyCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_FONT_FAMILY, value)

    def optionmenuUiLanguageCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_UI_LANGUAGE, value)

    def checkboxEnableRestoreMainWindowGeometryCallback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY, checkbox_box_widget.get())

    row=0
    config_window.sb__transparency = createSettingBoxSlider(
        for_var_label_text=view_variable.VAR_LABEL_TRANSPARENCY,
        for_var_desc_text=view_variable.VAR_DESC_TRANSPARENCY,
        slider_attr_name="sb__slider_transparency",
        slider_range=view_variable.SLIDER_RANGE_TRANSPARENCY,
        command=lambda value: sliderTransparencyCallback(value),
        variable=view_variable.VAR_TRANSPARENCY,
        slider_bind__ButtonPress=view_variable.CALLBACK_BUTTON_PRESS_TRANSPARENCY,
        slider_bind__ButtonRelease=view_variable.CALLBACK_BUTTON_RELEASE_TRANSPARENCY,
        sliderTooltipFormatter=view_variable.CALLBACK_SLIDER_TOOLTIP_PERCENTAGE_FORMATTER,
    )
    config_window.sb__transparency.grid(row=row)
    row+=1


    config_window.sb__appearance_theme = createSettingBoxDropdownMenu(
        for_var_label_text=view_variable.VAR_LABEL_APPEARANCE_THEME,
        for_var_desc_text=view_variable.VAR_DESC_APPEARANCE_THEME,
        optionmenu_attr_name="sb__optionmenu_appearance_theme",
        dropdown_menu_values=view_variable.LIST_APPEARANCE_THEME,
        command=lambda value: optionmenuAppearanceThemeCallback(value),
        variable=view_variable.VAR_APPEARANCE_THEME,
    )
    config_window.sb__appearance_theme.grid(row=row)
    row+=1



    config_window.sb__ui_scaling = createSettingBoxDropdownMenu(
        for_var_label_text=view_variable.VAR_LABEL_UI_SCALING,
        for_var_desc_text=view_variable.VAR_DESC_UI_SCALING,
        optionmenu_attr_name="sb__optionmenu_ui_scaling",
        dropdown_menu_values=view_variable.LIST_UI_SCALING,
        command=lambda value: optionmenuUiScalingCallback(value),
        variable=view_variable.VAR_UI_SCALING,
    )
    config_window.sb__ui_scaling.grid(row=row)
    row+=1

    config_window.sb__textbox_uis_scaling = createSettingBoxSlider(
        for_var_label_text=view_variable.VAR_LABEL_TEXTBOX_UI_SCALING,
        for_var_desc_text=view_variable.VAR_DESC_TEXTBOX_UI_SCALING,
        slider_attr_name="sb__slider_transparency",
        slider_range=view_variable.SLIDER_RANGE_TEXTBOX_UI_SCALING,
        command=lambda value: sliderTextBoxUiScalingCallback(value),
        variable=view_variable.VAR_TEXTBOX_UI_SCALING,
        slider_bind__ButtonPress=view_variable.CALLBACK_BUTTON_PRESS_TEXTBOX_UI_SCALING,
        slider_bind__ButtonRelease=view_variable.CALLBACK_BUTTON_RELEASE_TEXTBOX_UI_SCALING,
        sliderTooltipFormatter=view_variable.CALLBACK_SLIDER_TOOLTIP_PERCENTAGE_FORMATTER,
    )
    config_window.sb__textbox_uis_scaling.grid(row=row)
    row+=1

    config_window.sb__message_box_ratio = createSettingBoxSlider(
        for_var_label_text=view_variable.VAR_LABEL_MESSAGE_BOX_RATIO,
        for_var_desc_text=view_variable.VAR_DESC_MESSAGE_BOX_RATIO,
        slider_attr_name="sb__slider_message_box_ratio",
        slider_range=view_variable.SLIDER_RANGE_MESSAGE_BOX_RATIO,
        command=lambda value: sliderMessageBoxRatioCallback(value),
        variable=view_variable.VAR_MESSAGE_BOX_RATIO,
        slider_bind__ButtonPress=view_variable.CALLBACK_BUTTON_PRESS_MESSAGE_BOX_RATIO,
        slider_bind__ButtonRelease=view_variable.CALLBACK_BUTTON_RELEASE_MESSAGE_BOX_RATIO,
        sliderTooltipFormatter=view_variable.CALLBACK_SLIDER_TOOLTIP_PERCENTAGE_FORMATTER,
    )
    config_window.sb__message_box_ratio.grid(row=row)
    row+=1

    config_window.sb__font_family = createSettingBoxDropdownMenu(
        for_var_label_text=view_variable.VAR_LABEL_FONT_FAMILY,
        for_var_desc_text=view_variable.VAR_DESC_FONT_FAMILY,
        optionmenu_attr_name="sb__optionmenu_font_family",
        dropdown_menu_values=view_variable.LIST_FONT_FAMILY,
        command=lambda value: optionmenuFontFamilyCallback(value),
        variable=view_variable.VAR_FONT_FAMILY,
    )
    config_window.sb__font_family.grid(row=row)
    row+=1


    config_window.sb__ui_language = createSettingBoxDropdownMenu(
        for_var_label_text=view_variable.VAR_LABEL_UI_LANGUAGE,
        for_var_desc_text=view_variable.VAR_DESC_UI_LANGUAGE,
        optionmenu_attr_name="sb__optionmenu_ui_language",
        dropdown_menu_values=view_variable.LIST_UI_LANGUAGE,
        command=lambda value: optionmenuUiLanguageCallback(value),
        variable=view_variable.VAR_UI_LANGUAGE,
    )
    config_window.sb__ui_language.grid(row=row)
    row+=1

    config_window.sb__enable_restore_main_window_geometry = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY,
        checkbox_attr_name="sb__checkbox_enable_restore_main_window_geometry",
        command=lambda: checkboxEnableRestoreMainWindowGeometryCallback(config_window.sb__checkbox_enable_restore_main_window_geometry),
        variable=view_variable.VAR_ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY,
    )
    config_window.sb__enable_restore_main_window_geometry.grid(row=row, pady=0)
    row+=1