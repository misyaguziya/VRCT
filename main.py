from threading import Thread
from vrct_gui import vrct_gui
from config import config
from model import model

# func transcription
def sendMicMessage(message):
    if len(message) > 0:
        translation = ""
        if model.checkKeywords(message):
            logDetectWordFilter(message)
            return
        elif config.ENABLE_TRANSLATION is False:
            pass
        elif model.getTranslatorStatus() is False:
            pass
        else:
            translation = model.getInputTranslate(message)

        if config.ENABLE_OSC is True:
            osc_message = config.MESSAGE_FORMAT.replace("[message]", message)
            osc_message = osc_message.replace("[translation]", translation)
            model.oscSendMessage(osc_message)
        else:
            logOSCError()
        logTranscriptionSendMessage(message, translation)

def startTranscriptionSendMessage():
    model.startMicTranscript(sendMicMessage)

def stopTranscriptionSendMessage():
    model.stopMicTranscript()

# func print textbox
def logTranslationStatusChange():
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    if config.ENABLE_TRANSLATION:
        vrct_gui.printToTextbox(textbox_all, "翻訳機能をONにしました", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "翻訳機能をONにしました", "", "INFO")
    else:
        vrct_gui.printToTextbox(textbox_all, "翻訳機能をOFFにしました", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "翻訳機能をOFFにしました", "", "INFO")

def logTranscriptionSendStatusChange():
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    if config.ENABLE_TRANSCRIPTION_SEND:
        vrct_gui.printToTextbox(textbox_all, "Voice2chatbox機能をONにしました", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "Voice2chatbox機能をONにしました", "", "INFO")
    else:
        vrct_gui.printToTextbox(textbox_all, "Voice2chatbox機能をOFFにしました", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "Voice2chatbox機能をOFFにしました", "", "INFO")

def logTranscriptionSendMessage(message, translate):
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_sent = getattr(vrct_gui, "textbox_sent")
    vrct_gui.printToTextbox(textbox_all, message, translate, "SEND")
    vrct_gui.printToTextbox(textbox_sent, message, translate, "SEND")

def logDetectWordFilter(message):
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    vrct_gui.printToTextbox(textbox_all, f"Detect WordFilter :{message}", "", "INFO")
    vrct_gui.printToTextbox(textbox_system, f"Detect WordFilter :{message}", "", "INFO")

def logAuthenticationError():
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    vrct_gui.printToTextbox(textbox_all, "Auth Key or language setting is incorrect", "", "INFO")
    vrct_gui.printToTextbox(textbox_system, "Auth Key or language setting is incorrect", "", "INFO")

def logOSCError():
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    vrct_gui.printToTextbox(textbox_all, "OSC is not enabled, please enable OSC and rejoin", "", "INFO")
    vrct_gui.printToTextbox(textbox_system, "OSC is not enabled, please enable OSC and rejoin", "", "INFO")

# command func
def toggleTranslationFeature():
    config.ENABLE_TRANSLATION = getattr(vrct_gui, "translation_switch_box").get()
    logTranslationStatusChange()

def toggleTranscriptionSendFeature():
    config.ENABLE_TRANSCRIPTION_SEND = getattr(vrct_gui, "transcription_send_switch_box").get()
    if config.ENABLE_TRANSCRIPTION_SEND is True:
        th_startTranscriptionSendMessage = Thread(target=startTranscriptionSendMessage)
        th_startTranscriptionSendMessage.daemon = True
        th_startTranscriptionSendMessage.start()
    else:
        th_stopTranscriptionSendMessage = Thread(target=stopTranscriptionSendMessage)
        th_stopTranscriptionSendMessage.daemon = True
        th_stopTranscriptionSendMessage.start()
    logTranscriptionSendStatusChange()

# create GUI
vrct_gui.createGUI()

# init config
if model.authenticationTranslator() is False:
    # error update Auth key
    logAuthenticationError()

# set word filter
model.addKeywords()

# check OSC started
model.checkOSCStarted()

# check Software Updated
model.checkSoftwareUpdated()

# set commands
translation_switch_box = getattr(vrct_gui, "translation_switch_box")
translation_switch_box.configure(command=toggleTranslationFeature)
transcription_send_switch_box = getattr(vrct_gui, "transcription_send_switch_box")
transcription_send_switch_box.configure(command=toggleTranscriptionSendFeature)

if __name__ == "__main__":
    vrct_gui.startMainLoop()