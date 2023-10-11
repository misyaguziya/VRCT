from customtkinter import CTkImage, CTkLabel, CTkToplevel
from ..ui_utils import openImageKeepAspectRatio, getImageFileFromUiUtils
from time import sleep

class SplashWindow(CTkToplevel):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.overrideredirect(True)
        self.configure(fg_color="#292a2d")
        self.title("SplashWindow")


        sw=self.winfo_screenwidth()
        sh=self.winfo_screenheight()

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
        label.grid(row=1, column=1)

        geometry_width=desired_width+int(desired_width*0.2)
        geometry_height=height+int(height*0.5)

        self.geometry(str(geometry_width)+"x"+str(geometry_height)+"+"+str((sw-geometry_width)//2)+"+"+str((sh-geometry_height)//2))



    def showSplash(self):
        self.deiconify()

        for i in range(0,91,20):
            if not self.winfo_exists():
                break
            self.attributes("-alpha", i/100)
            self.update()
            sleep(1/50)
        self.attributes("-alpha", 1)


    def destroySplash(self):
        self.destroy()