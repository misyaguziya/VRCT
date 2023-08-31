from .widgets import createConfigWindowTitle, createSideMenuAndSettingsBoxContainers, createSettingBoxTopBar


from customtkinter import CTkToplevel

class ConfigWindow(CTkToplevel):
    def __init__(self, vrct_gui, settings):
        super().__init__()
        self.withdraw()


        # configure window
        self.title("test config_window.py")
        self.geometry(f"{1080}x{680}")


        self.configure(fg_color="#ff7f50")
        self.protocol("WM_DELETE_WINDOW", vrct_gui.closeConfigWindow)

        self.settings = settings


        # Appearance Tab
        self.CALLBACK_SET_TRANSPARENCY = None
        self.CALLBACK_SET_APPEARANCE = None
        self.CALLBACK_SET_UI_SCALING = None
        self.CALLBACK_SET_FONT_FAMILY = None
        self.CALLBACK_SET_UI_LANGUAGE = None

        # Translation Tab
        self.CALLBACK_SET_DEEPL_AUTHKEY = None

        # Transcription Tab (Mic)
        self.CALLBACK_SET_MIC_HOST = None
        self.CALLBACK_SET_MIC_DEVICE = None
        self.CALLBACK_SET_MIC_ENERGY_THRESHOLD = None
        self.CALLBACK_SET_MIC_DYNAMIC_ENERGY_THRESHOLD = None
        self.CALLBACK_CHECK_MIC_THRESHOLD = None
        self.CALLBACK_SET_MIC_RECORD_TIMEOUT = None
        self.CALLBACK_SET_MIC_PHRASE_TIMEOUT = None
        self.CALLBACK_SET_MIC_MAX_PHRASES = None
        self.CALLBACK_SET_MIC_WORD_FILTER = None

        # Transcription Tab (Speaker)
        self.CALLBACK_SET_SPEAKER_DEVICE = None
        self.CALLBACK_SET_SPEAKER_ENERGY_THRESHOLD = None
        self.CALLBACK_SET_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = None
        self.CALLBACK_CHECK_SPEAKER_THRESHOLD = None
        self.CALLBACK_SET_SPEAKER_RECORD_TIMEOUT = None
        self.CALLBACK_SET_SPEAKER_PHRASE_TIMEOUT = None
        self.CALLBACK_SET_SPEAKER_MAX_PHRASES = None

        # Others Tab
        self.CALLBACK_SET_ENABLE_AUTO_CLEAR_MESSAGE_BOX = None
        self.CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY = None
        self.CALLBACK_SET_MESSAGE_FORMAT = None

        # Advanced Settings Tab
        self.CALLBACK_SET_OSC_IP_ADDRESS = None
        self.CALLBACK_SET_OSC_PORT = None



        createConfigWindowTitle(config_window=self, settings=settings)

        createSettingBoxTopBar(config_window=self, settings=settings)


        createSideMenuAndSettingsBoxContainers(config_window=self, settings=settings)




    def reloadConfigWindowSettingBoxContainer(self):
        self.main_bg_container.destroy()
        createSideMenuAndSettingsBoxContainers(config_window=self, settings=self.settings)