from time import sleep

from customtkinter import StringVar, IntVar
from tkinter import font as tk_font
from languages import selectable_languages
from utils import get_key_by_value, callFunctionIfCallable


from .._SettingBoxGenerator import _SettingBoxGenerator

from config import config

def createSettingBox_Appearance(setting_box_wrapper, config_window, settings):
    sbg = _SettingBoxGenerator(config_window, settings)
    createSettingBoxDropdownMenu = sbg.createSettingBoxDropdownMenu
    createSettingBoxSlider = sbg.createSettingBoxSlider

    # 関数名は変えるかもしれない。
    # テーマ変更、フォント変更時、 Widget再生成か再起動かは検討中\
    def slider_transparency_callback(value):
        callFunctionIfCallable(config_window.CALLBACK_SET_TRANSPARENCY, value)

    def optionmenu_appearance_theme_callback(value):
        callFunctionIfCallable(config_window.CALLBACK_SET_APPEARANCE, value)

    def optionmenu_ui_scaling_callback(value):
        callFunctionIfCallable(config_window.CALLBACK_SET_UI_SCALING, value)
        # self.optionmenu_ui_scaling.set(choice)

    def optionmenu_font_family_callback(value):
        callFunctionIfCallable(config_window.CALLBACK_SET_FONT_FAMILY, value)

    def optionmenu_ui_language_callback(value):
        value = get_key_by_value(selectable_languages, value)
        callFunctionIfCallable(config_window.CALLBACK_SET_UI_LANGUAGE, value)


    row=0
    config_window.sb__transparency = createSettingBoxSlider(
        parent_widget=setting_box_wrapper,
        label_text="Transparency",
        desc_text="Change the window's transparency. 50% to 100%. (Default: 100%)",
        slider_attr_name="sb__transparency_slider",
        slider_range=(50, 100),
        command=lambda value: slider_transparency_callback(value),
        variable=IntVar(value=config.TRANSPARENCY),
    )
    config_window.sb__transparency.grid(row=row)
    row+=1


    config_window.sb__appearance_theme = createSettingBoxDropdownMenu(
        parent_widget=setting_box_wrapper,
        label_text="Theme",
        desc_text="Change the color theme from \"Light\" and \"Dark\". If you select \"System\", It will adjust based on your Windows theme. (Default: System)",
        optionmenu_attr_name="sb__optionmenu_appearance_theme",
        dropdown_menu_attr_name="sb__dropdown_appearance_theme",
        dropdown_menu_values=["Light", "Dark", "System"],
        command=lambda value: optionmenu_appearance_theme_callback(value),
        variable=StringVar(value=config.APPEARANCE_THEME)
    )
    config_window.sb__appearance_theme.grid(row=row)
    row+=1


    config_window.sb__ui_scaling = createSettingBoxDropdownMenu(
        parent_widget=setting_box_wrapper,
        label_text="UI Size",
        desc_text="(Default: 100%)",
        optionmenu_attr_name="sb__optionmenu_ui_scaling",
        dropdown_menu_attr_name="sb__dropdown_ui_scaling",
        dropdown_menu_values=["80%", "90%", "100%", "110%", "120%"],
        command=lambda value: optionmenu_ui_scaling_callback(value),
        variable=StringVar(value=config.UI_SCALING)
    )
    config_window.sb__ui_scaling.grid(row=row)
    row+=1


    # font_families = list(tk_font.families())
    config_window.sb__font_family = createSettingBoxDropdownMenu(
        parent_widget=setting_box_wrapper,
        label_text="Font Family",
        desc_text="(Default: Yu Gothic UI)",
        optionmenu_attr_name="sb__optionmenu_font_family",
        dropdown_menu_attr_name="sb__dropdown_font_family",
        dropdown_menu_values=["Font A", "Font B"],
        # dropdown_menu_values=font_families,
        command=lambda value: optionmenu_font_family_callback(value),
        variable=StringVar(value=config.FONT_FAMILY)
    )
    config_window.sb__font_family.grid(row=row)
    row+=1


    selectable_languages_values = list(selectable_languages.values())
    config_window.sb__ui_language = createSettingBoxDropdownMenu(
        parent_widget=setting_box_wrapper,
        label_text="UI Language",
        desc_text="(Default: English)",
        optionmenu_attr_name="sb__optionmenu_ui_language",
        dropdown_menu_attr_name="sb__dropdown_ui_language",
        dropdown_menu_values=selectable_languages_values,
        command=lambda value: optionmenu_ui_language_callback(value),
        variable=StringVar(value=selectable_languages[config.UI_LANGUAGE]),
    )
    config_window.sb__ui_language.grid(row=row)
    row+=1