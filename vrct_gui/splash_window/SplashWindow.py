import math
import time

from customtkinter import CTkImage, CTkLabel, CTkToplevel, CTkProgressBar, CTkFrame
from ..ui_utils import openImageKeepAspectRatio, getImageFileFromUiUtils, setGeometryToCenterOfScreen, fadeInAnimation

class SplashWindow(CTkToplevel):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.overrideredirect(True)
        self.configure(fg_color="#292a2d")
        self.title("SplashWindow")
        self.wm_attributes("-toolwindow", True)

        self.is_showed_weight_download_progressbar = False

        BG_HEIGHT= 220
        BG_WIDTH= 450
        BG_HEX_COLOR = "#292a2d"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.splash_background = CTkFrame(self, corner_radius=0, fg_color=BG_HEX_COLOR, width=BG_WIDTH, height=BG_HEIGHT)
        self.splash_background.grid()


        self.progressbar_wrapper = CTkFrame(self, corner_radius=0, fg_color=BG_HEX_COLOR, width=0, height=0)
        self.progressbar_wrapper.place(relx=0.5, rely=0.5, anchor="center")
        self.progressbar_wrapper.rowconfigure(0, minsize=BG_HEIGHT)

        PROGRESSBAR_HEIGHT = 3
        PROGRESSBAR_WIDTH = 60
        PROGRESSBAR_RIGHT_PADX = 38
        ALL_PROGRESSBAR_WIDTH = (PROGRESSBAR_WIDTH + PROGRESSBAR_RIGHT_PADX)*3 + PROGRESSBAR_WIDTH
        WHITE_HEX_COLOR = "#f2f2f2"
        VRCT_HEX_COLOR = "#48a495"
        column = 0

        for i in range(3):
            progressbar = CTkProgressBar(
                self.progressbar_wrapper,
                height=PROGRESSBAR_HEIGHT,
                width=PROGRESSBAR_WIDTH,
                corner_radius=0,
                fg_color=BG_HEX_COLOR,
                progress_color=WHITE_HEX_COLOR,
            )
            progressbar.set(0)
            progressbar.grid(row=0, column=column, padx=(0,PROGRESSBAR_RIGHT_PADX))

            setattr(self, "progressbar_" + str(i), progressbar)
            column+=1


        self.progressbar_3 = CTkProgressBar(
            self.progressbar_wrapper,
            height=PROGRESSBAR_HEIGHT,
            width=PROGRESSBAR_WIDTH,
            corner_radius=0,
            fg_color=BG_HEX_COLOR,
            progress_color=VRCT_HEX_COLOR,
        )
        self.progressbar_3.set(0)
        self.progressbar_3.grid(row=0, column=column, padx=0)



        self.chato_img_mask_frame = CTkFrame(self.progressbar_wrapper, corner_radius=0, fg_color=BG_HEX_COLOR, width=ALL_PROGRESSBAR_WIDTH, height=0)
        self.chato_img_mask_frame.place(relx=1, rely=0.49, relheight=0.5, anchor="se")


        CHATO_POSITION = int( (ALL_PROGRESSBAR_WIDTH-(PROGRESSBAR_WIDTH/2)) + 2)
        (self.chato_img, self.CHATO_IMG_WIDTH, self.CHATO_IMG_HEIGHT) = openImageKeepAspectRatio(getImageFileFromUiUtils("vrct_logo_mark_white_square.png"), int(PROGRESSBAR_WIDTH - (PROGRESSBAR_WIDTH/5)))

        self.chato_img_label = CTkLabel(
            self.chato_img_mask_frame,
            text=None,
            height=0,
            fg_color=BG_HEX_COLOR,
            image=CTkImage(self.chato_img, size=(self.CHATO_IMG_WIDTH, self.CHATO_IMG_HEIGHT))
        )
        self.chato_img_label.place(x=CHATO_POSITION, rely=1, relwidth=1, anchor="n")



        (img, desired_width, height) = openImageKeepAspectRatio(getImageFileFromUiUtils("VRCT_starting_up.png"), 100)
        self.starting_up_text_label = CTkLabel(
            self,
            text=None,
            height=0,
            fg_color=BG_HEX_COLOR,
            image=CTkImage(img, size=(desired_width, height))
        )
        self.starting_up_text_label.place(relx=0.5, rely=0.7, anchor="center")



        (self.vrct_second_text_img, desired_width, height) = openImageKeepAspectRatio(getImageFileFromUiUtils("vrchat_chatbox_trasnlator_transcription.png"), 280)
        self.vrct_second_text_img_label = CTkLabel(
            self,
            text=None,
            height=0,
            fg_color=BG_HEX_COLOR,
            image=CTkImage(self.vrct_second_text_img, size=(desired_width, height))
        )
        self.vrct_second_text_img_label.place(relx=0.98, rely=0.98, anchor="se")




        (self.vrct_logo_img, desired_width, height) = openImageKeepAspectRatio(getImageFileFromUiUtils("vrct_logo_for_dark_mode.png"), 280)
        self.vrct_logo_img_label = CTkLabel(
            self,
            text=None,
            height=0,
            fg_color=BG_HEX_COLOR,
            image=CTkImage(self.vrct_logo_img, size=(desired_width, height))
        )




        self.weight_download_progressbar_widget = CTkProgressBar(
            self,
            height=8,
            corner_radius=0,
            fg_color="#4b4c4f",
            progress_color=VRCT_HEX_COLOR,
        )
        self.weight_download_progressbar_widget.set(0)


        (img, desired_width, height) = openImageKeepAspectRatio(getImageFileFromUiUtils("VRCT_now_downloading.png"), 320)
        self.weight_download_text_label = CTkLabel(
            self,
            text=None,
            height=0,
            fg_color=BG_HEX_COLOR,
            image=CTkImage(img, size=(desired_width, height))
        )


    def toProgress(self, num:int):
        if self.is_showed_weight_download_progressbar is True:
            self.vrct_logo_img_label.place_forget()
            self.weight_download_progressbar_widget.place_forget()
            self.weight_download_text_label.place_forget()

            self.progressbar_wrapper.place(relx=0.5, rely=0.5, anchor="center")
            self.starting_up_text_label.place(relx=0.5, rely=0.7, anchor="center")
            self.vrct_second_text_img_label.place(relx=0.98, rely=0.98, anchor="se")
            self.update()

        target_progressbar_widget = getattr(self, "progressbar_" + str(num))

        # This animation process' base code was made by ChatGPT.
        start_time = time.time()
        DURATION = 0.2
        while True:
            elapsed_time = time.time() - start_time
            progress = min(elapsed_time / DURATION, 1.0)
            eased_progress = 1 - math.pow(1 - progress, 6)


            target_progressbar_widget.set(eased_progress)
            self.update_idletasks()

            if elapsed_time >= DURATION:
                break

            time.sleep(0.01)

        DURATION = 0.2
        if num == 3:
            start_time = time.time()
            while True:
                elapsed_time = time.time() - start_time
                progress = min(elapsed_time / DURATION, 1.0)
                eased_progress = 1 - math.pow(1 - progress, 6)

                # angleが45度未満の場合は0から45度に進むようにし、45度以上の場合は45度に固定
                angle = min(45, 45 * eased_progress)
                angle = -angle

                rotated_img = self.rotateImage(self.chato_img, angle)
                self.chato_img_label.configure(image=CTkImage(rotated_img, size=(self.CHATO_IMG_WIDTH, self.CHATO_IMG_HEIGHT)))

                rely = 1.0 - eased_progress * 0.6
                self.chato_img_label.place_configure(rely=rely)
                self.update()

                if elapsed_time >= DURATION:
                    break

                time.sleep(0.01)

    def rotateImage(self, image, angle):
        # 画像を回転させる
        rotated_image = image.rotate(angle, expand=True)
        return rotated_image

        # This making gradient color process was made by ChatGPT.
    def generateGradientColor(self, value):
        # 0の時の色と1の時の色を指定
        color_start = [242, 242, 242]  # RGB values for #f2f2f2
        color_end = [72, 164, 149]    # RGB values for #48a495

        # 補完色を計算
        interpolated_color = [
            int(start + (end - start) * value) for start, end in zip(color_start, color_end)
        ]

        # RGB値を0から255の範囲にクリップ
        interpolated_color = [max(0, min(255, val)) for val in interpolated_color]

        # RGBを16進数に変換
        hex_color = "#{:02x}{:02x}{:02x}".format(*interpolated_color)

        return hex_color


    def updateDownloadProgress(self, progress:float):
        if self.is_showed_weight_download_progressbar is False:
            self.vrct_second_text_img_label.place_forget()
            self.progressbar_wrapper.place_forget()
            self.starting_up_text_label.place_forget()

            self.vrct_logo_img_label.place(relx=0.5, rely=0.4, anchor="center")
            self.weight_download_progressbar_widget.place(relwidth=0.9, relx=0.5, rely=0.84, anchor="s")
            self.weight_download_text_label.place(relx=0.98, rely=0.96, anchor="se")
            self.is_showed_weight_download_progressbar = True
            self.update()

        progress_color = self.generateGradientColor(progress)
        self.weight_download_progressbar_widget.configure(progress_color=progress_color)
        self.weight_download_progressbar_widget.set(progress)
        self.update_idletasks()


    def showSplash(self):
        self.attributes("-alpha", 0)
        self.deiconify()
        setGeometryToCenterOfScreen(root_widget=self)
        fadeInAnimation(self, steps=5, interval=0.02)


    def destroySplash(self):
        self.destroy()