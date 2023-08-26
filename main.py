from vrct_gui import vrct_gui
from config import config
from model import model

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

# command func
def toggleTranslationFeature():
    config.ENABLE_TRANSLATION = getattr(vrct_gui, "translation_switch_box").get()
    logTranslationStatusChange()

# create GUI
vrct_gui.createGUI()

# set commands
widget = getattr(vrct_gui, "translation_switch_box")
widget.configure(command=toggleTranslationFeature)


if __name__ == "__main__":
    vrct_gui.startMainLoop()