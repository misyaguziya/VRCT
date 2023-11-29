from customtkinter import CTkImage, CTkLabel, CTkToplevel, CTkProgressBar
from ..ui_utils import openImageKeepAspectRatio, getImageFileFromUiUtils, setGeometryToCenterOfScreen, fadeInAnimation

class SplashWindow(CTkToplevel):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.overrideredirect(True)
        self.configure(fg_color="#292a2d")
        self.title("SplashWindow")
        self.wm_attributes("-toolwindow", True)

        self.is_showed_progressbar = False

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


        self.progressbar_widget = CTkProgressBar(
            self,
            height=10,
            corner_radius=0,
            fg_color="#4b4c4f",
            progress_color="#48a495",
        )
        self.progressbar_widget.set(0)


        (img, desired_width, height) = openImageKeepAspectRatio(getImageFileFromUiUtils("VRCT_now_downloading.png"), 320)
        self.text_label = CTkLabel(
            self,
            text=None,
            height=0,
            fg_color="#292a2d",
            image=CTkImage(img, size=(desired_width, height))
        )



    def updateDownloadProgress(self, progress:float):
        if self.is_showed_progressbar is False:
            self.progressbar_widget.place(relwidth=0.9, relx=0.5, rely=0.9, anchor="s")
            self.text_label.place(relx=0.98, rely=0.98, anchor="se")
            self.is_showed_progressbar = True

        self.progressbar_widget.set(progress)
        self.update_idletasks()


    def showSplash(self):
        self.attributes("-alpha", 0)
        self.deiconify()
        setGeometryToCenterOfScreen(root_widget=self)
        fadeInAnimation(self, steps=5, interval=0.02)


    def destroySplash(self):
        self.destroy()