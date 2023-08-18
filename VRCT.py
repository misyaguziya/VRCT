from time import sleep
from os import path as os_path

import customtkinter
from customtkinter import CTk, CTkFrame, CTkCheckBox, CTkFont, CTkButton, CTkImage, CTkTabview, CTkTextbox, CTkEntry
from PIL.Image import open as Image_open

from threading import Thread
from utils import print_textbox, get_localized_text, widget_main_window_label_setter
from window_config import ToplevelWindowConfig
from window_information import ToplevelWindowInformation
from config import config
from model import model

class App(CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ## set UI theme
        customtkinter.set_appearance_mode(config.APPEARANCE_THEME)
        customtkinter.set_default_color_theme("blue")

        # init main window
        self.iconbitmap(os_path.join(os_path.dirname(__file__), "img", "app.ico"))
        self.title("VRCT")
        self.geometry(f"{400}x{175}")
        self.minsize(400, 175)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.wm_attributes("-alpha", config.TRANSPARENCY/100)
        customtkinter.set_widget_scaling(int(config.UI_SCALING.replace("%", "")) / 100)
        self.protocol("WM_DELETE_WINDOW", self.delete_window)

        # add sidebar
        self.add_sidebar()

        # add entry message box
        self.entry_message_box = CTkEntry(
            self,
            placeholder_text="message",
            font=CTkFont(family=config.FONT_FAMILY),
        )
        self.entry_message_box.grid(row=1, column=1, columnspan=2, padx=5, pady=(5, 10), sticky="nsew")
        self.entry_message_box.bind("<Return>", self.entry_message_box_press_key_enter)
        self.entry_message_box.bind("<Any-KeyPress>", self.entry_message_box_press_key_any)
        self.entry_message_box.bind("<Leave>", self.entry_message_box_leave)

        # add tabview textbox
        self.add_tabview_logs(get_localized_text(f"{config.UI_LANGUAGE}"))

        self.config_window = ToplevelWindowConfig(self)
        self.information_window = ToplevelWindowInformation(self)
        self.init_process()

    def init_process(self):
        # set translator
        if model.authenticationTranslator() is False:
            # error update Auth key
            print_textbox(self.textbox_message_log, "Auth Key or language setting is incorrect", "ERROR")
            print_textbox(self.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")

        # set word filter
        model.addKeywords()

        # check OSC started
        model.oscCheck()

    def button_config_callback(self):
        self.foreground_stop()
        self.transcription_stop()
        self.checkbox_translation.configure(state="disabled")
        self.checkbox_transcription_send.configure(state="disabled")
        self.checkbox_transcription_receive.configure(state="disabled")
        self.checkbox_foreground.configure(state="disabled")
        self.tabview_logs.configure(state="disabled")
        self.textbox_message_log.configure(state="disabled")
        self.textbox_message_send_log.configure(state="disabled")
        self.textbox_message_receive_log.configure(state="disabled")
        self.textbox_message_system_log.configure(state="disabled")
        self.entry_message_box.configure(state="disabled")
        self.button_config.configure(state="disabled", fg_color=["gray92", "gray14"])
        self.button_information.configure(state="disabled", fg_color=["gray92", "gray14"])
        self.config_window.deiconify()
        self.config_window.focus_set()
        self.config_window.focus()
        self.config_window.grab_set()

    def button_information_callback(self):
        self.information_window.deiconify()
        self.information_window.focus_set()
        self.information_window.focus()

    def checkbox_translation_callback(self):
        config.ENABLE_TRANSLATION = self.checkbox_translation.get()
        if config.ENABLE_TRANSLATION is True:
            print_textbox(self.textbox_message_log, "Start translation", "INFO")
            print_textbox(self.textbox_message_system_log, "Start translation", "INFO")
        else:
            print_textbox(self.textbox_message_log, "Stop translation", "INFO")
            print_textbox(self.textbox_message_system_log, "Stop translation", "INFO")

    def transcription_send_start(self):
        model.startMicTranscript(self.textbox_message_log, self.textbox_message_send_log, self.textbox_message_system_log)
        print_textbox(self.textbox_message_log, "Start voice2chatbox", "INFO")
        print_textbox(self.textbox_message_system_log, "Start voice2chatbox", "INFO")
        self.checkbox_transcription_send.configure(state="normal")
        self.checkbox_transcription_receive.configure(state="normal")
        self.button_config.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])

    def transcription_send_stop(self):
        model.stopMicTranscript()
        print_textbox(self.textbox_message_log, "Stop voice2chatbox", "INFO")
        print_textbox(self.textbox_message_system_log, "Stop voice2chatbox", "INFO")
        self.checkbox_transcription_send.configure(state="normal")
        self.checkbox_transcription_receive.configure(state="normal")
        self.button_config.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])

    def transcription_send_stop_for_config(self):
        model.stopMicTranscript()
        print_textbox(self.textbox_message_log, "Stop voice2chatbox", "INFO")
        print_textbox(self.textbox_message_system_log, "Stop voice2chatbox", "INFO")

    def checkbox_transcription_send_callback(self):
        config.ENABLE_TRANSCRIPTION_SEND = self.checkbox_transcription_send.get()
        self.checkbox_transcription_send.configure(state="disabled")
        self.checkbox_transcription_receive.configure(state="disabled")
        self.button_config.configure(state="disabled", fg_color=["gray92", "gray14"])
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            th_transcription_send_start = Thread(target=self.transcription_send_start)
            th_transcription_send_start.daemon = True
            th_transcription_send_start.start()
        else:
            th_transcription_send_stop = Thread(target=self.transcription_send_stop)
            th_transcription_send_stop.daemon = True
            th_transcription_send_stop.start()

    def transcription_receive_start(self):
        model.startSpeakerTranscript(self.textbox_message_log, self.textbox_message_receive_log, self.textbox_message_system_log)
        print_textbox(self.textbox_message_log,  "Start speaker2log", "INFO")
        print_textbox(self.textbox_message_system_log, "Start speaker2log", "INFO")
        self.checkbox_transcription_send.configure(state="normal")
        self.checkbox_transcription_receive.configure(state="normal")
        self.button_config.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])

    def transcription_receive_stop(self):
        model.stopSpeakerTranscript()
        print_textbox(self.textbox_message_log,  "Stop speaker2log", "INFO")
        print_textbox(self.textbox_message_system_log, "Stop speaker2log", "INFO")
        self.checkbox_transcription_send.configure(state="normal")
        self.checkbox_transcription_receive.configure(state="normal")
        self.button_config.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])

    def transcription_receive_stop_for_config(self):
        model.stopSpeakerTranscript()
        print_textbox(self.textbox_message_log,  "Stop speaker2log", "INFO")
        print_textbox(self.textbox_message_system_log, "Stop speaker2log", "INFO")

    def checkbox_transcription_receive_callback(self):
        config.ENABLE_TRANSCRIPTION_RECEIVE = self.checkbox_transcription_receive.get()
        self.checkbox_transcription_send.configure(state="disabled")
        self.checkbox_transcription_receive.configure(state="disabled")
        self.button_config.configure(state="disabled", fg_color=["gray92", "gray14"])
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            th_transcription_receive_start = Thread(target=self.transcription_receive_start)
            th_transcription_receive_start.daemon = True
            th_transcription_receive_start.start()
        else:
            th_transcription_receive_stop = Thread(target=self.transcription_receive_stop)
            th_transcription_receive_stop.daemon = True
            th_transcription_receive_stop.start()

    def transcription_start(self):
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            th_transcription_send_start = Thread(target=self.transcription_send_start)
            th_transcription_send_start.daemon = True
            th_transcription_send_start.start()
            sleep(2)
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            th_transcription_receive_start = Thread(target=self.transcription_receive_start)
            th_transcription_receive_start.daemon = True
            th_transcription_receive_start.start()

    def transcription_stop(self):
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            th_transcription_send_stop = Thread(target=self.transcription_send_stop_for_config)
            th_transcription_send_stop.daemon = True
            th_transcription_send_stop.start()
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            th_transcription_receive_stop = Thread(target=self.transcription_receive_stop_for_config)
            th_transcription_receive_stop.daemon = True
            th_transcription_receive_stop.start()

    def checkbox_foreground_callback(self):
        config.ENABLE_FOREGROUND = self.checkbox_foreground.get()
        if config.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)
            print_textbox(self.textbox_message_log,  "Start foreground", "INFO")
            print_textbox(self.textbox_message_system_log, "Start foreground", "INFO")
        else:
            self.attributes("-topmost", False)
            print_textbox(self.textbox_message_log,  "Stop foreground", "INFO")
            print_textbox(self.textbox_message_system_log, "Stop foreground", "INFO")

    def foreground_start(self):
        if config.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)
            print_textbox(self.textbox_message_log,  "Start foreground", "INFO")
            print_textbox(self.textbox_message_system_log, "Start foreground", "INFO")

    def foreground_stop(self):
        if config.ENABLE_FOREGROUND:
            self.attributes("-topmost", False)
            print_textbox(self.textbox_message_log,  "Stop foreground", "INFO")
            print_textbox(self.textbox_message_system_log, "Stop foreground", "INFO")

    def entry_message_box_press_key_enter(self, event):
        # osc stop send typing
        model.oscStopSendTyping()

        if config.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)

        message = self.entry_message_box.get()
        if len(message) > 0:
            # translate
            if config.ENABLE_TRANSLATION is False:
                chat_message = f"{message}"
            elif model.getTranslatorStatus() is False:
                print_textbox(self.textbox_message_log,  "Auth Key or language setting is incorrect", "ERROR")
                print_textbox(self.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")
                chat_message = f"{message}"
            else:
                chat_message = model.getInputTranslate(message)

            # send OSC message
            if config.ENABLE_OSC is True:
                model.oscSendMessage(chat_message)
            else:
                print_textbox(self.textbox_message_log, "OSC is not enabled, please enable OSC and rejoin.", "ERROR")
                print_textbox(self.textbox_message_system_log, "OSC is not enabled, please enable OSC and rejoin.", "ERROR")

            # update textbox message log
            print_textbox(self.textbox_message_log,  f"{chat_message}", "SEND")
            print_textbox(self.textbox_message_send_log, f"{chat_message}", "SEND")

            # delete message in entry message box
            if config.ENABLE_AUTO_CLEAR_CHATBOX is True:
                self.entry_message_box.delete(0, customtkinter.END)

    def entry_message_box_press_key_any(self, event):
        # osc start send typing
        model.oscStartSendTyping()
        if config.ENABLE_FOREGROUND:
            self.attributes("-topmost", False)

        if event.keysym != "??":
            if len(event.char) != 0 and event.keysym in config.BREAK_KEYSYM_LIST:
                self.entry_message_box.insert("end", event.char)
                return "break"

    def entry_message_box_leave(self, event):
        # osc stop send typing
        model.oscStopSendTyping()
        if config.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)

    def delete_window(self):
        self.quit()
        self.destroy()

    def add_sidebar(self):
        init_lang_text = "Loading..."
        self.sidebar_frame = CTkFrame(master=self, corner_radius=0)

        # add checkbox translation
        self.checkbox_translation = CTkCheckBox(
            self.sidebar_frame,
            text=init_lang_text,
            onvalue=True,
            offvalue=False,
            command=self.checkbox_translation_callback,
            font=CTkFont(family=config.FONT_FAMILY)
        )

        # add checkbox transcription send
        self.checkbox_transcription_send = CTkCheckBox(
            self.sidebar_frame,
            text=init_lang_text,
            onvalue=True,
            offvalue=False,
            command=self.checkbox_transcription_send_callback,
            font=CTkFont(family=config.FONT_FAMILY)
        )

        # add checkbox transcription receive
        self.checkbox_transcription_receive = CTkCheckBox(
            self.sidebar_frame,
            text=init_lang_text,
            onvalue=True,
            offvalue=False,
            command=self.checkbox_transcription_receive_callback,
            font=CTkFont(family=config.FONT_FAMILY)
        )

        # add checkbox foreground
        self.checkbox_foreground = CTkCheckBox(
            self.sidebar_frame,
            text=init_lang_text,
            onvalue=True,
            offvalue=False,
            command=self.checkbox_foreground_callback,
            font=CTkFont(family=config.FONT_FAMILY)
        )

        # add button information
        self.button_information = CTkButton(
            self.sidebar_frame,
            text=None,
            width=36,
            command=self.button_information_callback,
            image=CTkImage(Image_open(os_path.join(os_path.dirname(__file__), "img", "info-icon-white.png")))
        )

        # add button config
        self.button_config = CTkButton(
            self.sidebar_frame,
            text=None,
            width=36,
            command=self.button_config_callback,
            image=CTkImage(Image_open(os_path.join(os_path.dirname(__file__), "img", "config-icon-white.png")))
        )

        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsw")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)
        self.checkbox_translation.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="we")
        self.checkbox_transcription_send.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="we")
        self.checkbox_transcription_receive.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="we")
        self.checkbox_foreground.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="we")
        self.button_information.grid(row=5, column=0, padx=(10, 5), pady=(5, 5), sticky="wse")
        self.button_config.grid(row=5, column=1, padx=(5, 10), pady=(5, 5), sticky="wse")

    def delete_tabview_logs(self, pre_language_yaml_data):
        self.tabview_logs.delete(pre_language_yaml_data["main_tab_title_log"])
        self.tabview_logs.delete(pre_language_yaml_data["main_tab_title_send"])
        self.tabview_logs.delete(pre_language_yaml_data["main_tab_title_receive"])
        self.tabview_logs.delete(pre_language_yaml_data["main_tab_title_system"])

    def add_tabview_logs(self, language_yaml_data):
        main_tab_title_log = language_yaml_data["main_tab_title_log"]
        main_tab_title_send = language_yaml_data["main_tab_title_send"]
        main_tab_title_receive = language_yaml_data["main_tab_title_receive"]
        main_tab_title_system = language_yaml_data["main_tab_title_system"]

        # add tabview textbox
        self.tabview_logs = CTkTabview(master=self)
        self.tabview_logs.add(main_tab_title_log)
        self.tabview_logs.add(main_tab_title_send)
        self.tabview_logs.add(main_tab_title_receive)
        self.tabview_logs.add(main_tab_title_system)
        self.tabview_logs.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        self.tabview_logs._segmented_button.configure(font=CTkFont(family=config.FONT_FAMILY))
        self.tabview_logs._segmented_button.grid(sticky="W")
        self.tabview_logs.tab(main_tab_title_log).grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_log).grid_columnconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_send).grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_send).grid_columnconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_receive).grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_receive).grid_columnconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_system).grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_system).grid_columnconfigure(0, weight=1)
        self.tabview_logs.configure(fg_color="transparent")

        # add textbox message log
        self.textbox_message_log = CTkTextbox(
            self.tabview_logs.tab(main_tab_title_log),
            font=CTkFont(family=config.FONT_FAMILY)
        )

        # add textbox message send log
        self.textbox_message_send_log = CTkTextbox(
            self.tabview_logs.tab(main_tab_title_send),
            font=CTkFont(family=config.FONT_FAMILY)
        )

        # add textbox message receive log
        self.textbox_message_receive_log = CTkTextbox(
            self.tabview_logs.tab(main_tab_title_receive),
            font=CTkFont(family=config.FONT_FAMILY)
        )

        # add textbox message system log
        self.textbox_message_system_log = CTkTextbox(
            self.tabview_logs.tab(main_tab_title_system),
            font=CTkFont(family=config.FONT_FAMILY)
        )

        self.textbox_message_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_send_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_receive_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_system_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_log.configure(state='disabled')
        self.textbox_message_send_log.configure(state='disabled')
        self.textbox_message_receive_log.configure(state='disabled')
        self.textbox_message_system_log.configure(state='disabled')

        widget_main_window_label_setter(self, language_yaml_data)

if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        import traceback
        with open('error.log', 'a') as f:
            traceback.print_exc(file=f)