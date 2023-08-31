from time import sleep

from customtkinter import StringVar, IntVar

from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

from config import config

def createSettingBox_AdvancedSettings(setting_box_wrapper, config_window, settings):
    sbg = _SettingBoxGenerator(config_window, settings)
    createSettingBoxEntry = sbg.createSettingBoxEntry


    def entry_ip_address_callback(value):
        callFunctionIfCallable(config_window.CALLBACK_SET_OSC_IP_ADDRESS, value)

    def entry_port_callback(value):
        callFunctionIfCallable(config_window.CALLBACK_SET_OSC_PORT, value)

    row=0
    config_window.sb__ip_address = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        label_text="OSC IP Address",
        desc_text="(Default: 127.0.0.1)",
        entry_attr_name="sb__entry_ip_address",
        entry_width=settings.uism.SB__ENTRY_WIDTH_150,
        entry_bind__Any_KeyRelease=lambda value: entry_ip_address_callback(value),
        entry_textvariable=StringVar(value=config.OSC_IP_ADDRESS),
    )
    config_window.sb__ip_address.grid(row=row)
    row+=1


    config_window.sb__port = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        label_text="OSC Port",
        desc_text="(Default: 9000)",
        entry_attr_name="sb__entry_port",
        entry_width=settings.uism.SB__ENTRY_WIDTH_150,
        entry_bind__Any_KeyRelease=lambda value: entry_port_callback(value),
        entry_textvariable=IntVar(value=config.OSC_PORT),
    )
    config_window.sb__port.grid(row=row)
    row+=1