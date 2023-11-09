from customtkinter import CTkImage, CTkLabel, CTkToplevel
from ..ui_utils import openImageKeepAspectRatio, getImageFileFromUiUtils, setGeometryToCenterOfScreen, fadeInAnimation

class SplashWindow(CTkToplevel):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.overrideredirect(True)
        self.configure(fg_color="#292a2d")
        self.title("SplashWindow")
        self.wm_attributes("-toolwindow", True)


        sw=self.winfo_screenwidth()

        pw=int(sw/4)

        self.grid_columnconfigure((0,2), weight=1)
        self.grid_rowconfigure((0,2), weight=1)
        (img, desired_width, height) = openImageKeepAspectRatio(getImageFileFromUiUtils("vrct_logo_for_dark_mode.png"), pw)
        label = CTkLabel(
            self,
            text=None,
            height=0,
            fg_color="#292a2d",
            image=CTkImage(img, size=(desired_width, height))
        )
        label.grid(row=1, column=1, padx=int(desired_width/7), pady=int(height/3))


    def showSplash(self):
        self.attributes("-alpha", 0)
        self.deiconify()
        setGeometryToCenterOfScreen(root_widget=self)
        fadeInAnimation(self, steps=5, interval=0.02)


    def destroySplash(self):
        self.destroy()