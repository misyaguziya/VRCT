from time import sleep

from customtkinter import StringVar, IntVar


from .._SettingBoxGenerator import _SettingBoxGenerator

from config import config

def createSettingBox_Translation(setting_box_wrapper, config_window, settings):
    sbg = _SettingBoxGenerator(config_window, settings)
    createSettingBoxEntry = sbg.createSettingBoxEntry


    def deepl_authkey_callback(value):
        print(str(value))
        # config.AUTH_KEYS["DeepL(auth)"] = str(value)
        # if len(value) > 0:
        #     if model.authenticationTranslator(choice_translator="DeepL(auth)", auth_key=value) is True:
        #         print_textbox(self.parent.textbox_message_log, "Auth key update completed", "INFO")
        #         print_textbox(self.parent.textbox_message_system_log, "Auth key update completed", "INFO")
        #     else:
        #         pass


    row=0
    config_window.sb__deepl_authkey = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        label_text="DeepL Auth Key",
        desc_text="",
        entry_attr_name="sb__deepl_authkey",
        entry_width=settings.uism.SB__ENTRY_WIDTH_300,
        entry_bind__Any_KeyRelease=lambda value: deepl_authkey_callback(value),
        entry_textvariable=StringVar(value=config.AUTH_KEYS["DeepL(auth)"]),
    )
    config_window.sb__deepl_authkey.grid(row=row)
    row+=1