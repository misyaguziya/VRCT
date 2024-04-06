from types import SimpleNamespace

from ..ui_utils import calculateUiSize, getImageFileFromUiUtils_AboutVrct, bindButtonReleaseFunction, createButtonWithImage, bindButtonFunctionAndColor
from customtkinter import CTkFrame, CTkLabel, CTkImage, CTkFont

IMAGE_STANDARD_SCALING = 2
class AboutVrctManager():
    def __init__(self, scaling_percentage, ui_language, ctm):
        self.ctm = ctm
        scaling_float = int(scaling_percentage.replace("%", "")) / 100
        self.SCALING_FLOAT = max(scaling_float, 0.4)

        self.uism = SimpleNamespace()

        self.uism.ABOUT_VRCT_CONTAINER_LEFT_PADX = self.dupTuple(self._calculateUiSize(32))

        self.uism.SECTION_BOTTOM_PADY = self._calculateUiSize(22)
        self.uism.PROJECT_LINKS_SECTION_BOTTOM_PADDING = self._calculateUiSize(18) # Exception pady

        self.uism.VRCHAT_DISCLAIMER_SECTION_TOP_PADDING = self._calculateUiSize(80) # Exception pady

        self.uism.THE_DEVELOPERS_SECTION_TITLE_BOTTOM_PADY = self._calculateUiSize(8)
        self.uism.DEVS_CONTACTS_Y1 = self._calculateUiSize(118)
        self.uism.DEVS_MISYA_X_X = self._calculateUiSize(269)
        self.uism.DEVS_MISYA_GITHUB_X = self._calculateUiSize(297)
        self.uism.DEVS_SHIINA_X_X = self._calculateUiSize(298)

        self.uism.PROJECT_LINK_BOTTOM_PADY = self._calculateUiSize(2)
        self.uism.PROJECT_LINK_CORNER_RADIUS = self._calculateUiSize(4)
        self.uism.PROJECT_LINK_CONTENTS_PADX = self._calculateUiSize(55)
        self.uism.PROJECT_LINK_ITEM_IPADX = self._calculateUiSize(10)
        self.uism.PROJECT_LINK_ITEM_IPADY = self._calculateUiSize(4)

        self.uism.CONTRIBUTORS_SECTION_TITLE_BOTTOM_PADY = self._calculateUiSize(10)

        self.uism.CONTRIBUTORS_CONTACTS_Y1 = self._calculateUiSize(66)
        self.uism.CONTRIBUTORS_DONE_SAN_X_X = self._calculateUiSize(25)
        self.uism.CONTRIBUTORS_IYA_X_X = self._calculateUiSize(281)
        self.uism.CONTRIBUTORS_RERA_X_X = self._calculateUiSize(530)
        self.uism.CONTRIBUTORS_RERA_GITHUB_X = self._calculateUiSize(554)

        self.uism.CONTRIBUTORS_CONTACTS_Y2 = self._calculateUiSize(170)
        self.uism.CONTRIBUTORS_POPOSUKE_X_X = self._calculateUiSize(154)
        self.uism.CONTRIBUTORS_KUMAGUMA_X_X = self._calculateUiSize(413)


        self.uism.TELL_US_BUTTON_CORNER_RADIUS = self._calculateUiSize(6)
        self.uism.TELL_US_BUTTON_PADX = self._calculateUiSize(8)
        self.uism.TELL_US_BUTTON_PADY = self._calculateUiSize(8)
        self.uism.TELL_US_BUTTON_BORDER_WIDTH = self._calculateUiSize(1)


        self.uism.SPECIAL_THANKS_SECTION_TITLE_BOTTOM_PADY = self._calculateUiSize(6)
        self.uism.SPECIAL_THANKS_MEMBERS_BOTTOM_PADY = self._calculateUiSize(4)
        self.uism.SPECIAL_THANKS_MESSAGE_BOTTOM_PADY = self._calculateUiSize(0)
        self.uism.SPECIAL_THANKS_MESSAGE_AND_YOU_BOTTOM_PADY = self._calculateUiSize(8)

        self.uism.POSTER_SHOWCASE_SECTION_TITLE_BOTTOM_PADY = self._calculateUiSize(6)
        self.uism.POSTER_SHOWCASE_POSTER_IMAGES_BOTTOM_PADY = self._calculateUiSize(18)
        self.uism.POSTER_SHOWCASE_WORLD_ITEM_BOTTOM_PADY = self._calculateUiSize(4)
        self.uism.POSTER_SHOWCASE_WORLD_ITEM_IPADX = self._calculateUiSize(12)
        self.uism.POSTER_SHOWCASE_WORLD_ITEM_IPADY = self._calculateUiSize(4)
        self.uism.POSTER_SHOWCASE_WORLD_BOTTOM_PADY = self._calculateUiSize(4)
        self.uism.POSTER_SHOWCASE_WORLD_CORNER_RADIUS = self._calculateUiSize(4)
        self.uism.POSTER_TELL_US_MESSAGE_TOP_PADY = self._calculateUiSize(20)
        self.uism.POSTER_CHANGE_BUTTON_CORNER_RADIUS = self._calculateUiSize(6)


        self.image_file = SimpleNamespace()


        if ui_language == "ja":
            self.image_file.SPECIAL_THANKS_MESSAGE = "special_thanks_message_ja.png"
            self.image_file.SPECIAL_THANKS_TELL_US_MESSAGE = "special_thanks_tell_us_message_ja.png"
            self.image_file.POSTER_TELL_US_MESSAGE = "poster_tell_us_message_ja.png"
        else:
            self.image_file.SPECIAL_THANKS_MESSAGE = "special_thanks_message_en.png"
            self.image_file.SPECIAL_THANKS_TELL_US_MESSAGE = "special_thanks_tell_us_message_en.png"
            self.image_file.POSTER_TELL_US_MESSAGE = "poster_tell_us_message_en.png"

        poster_showcase_pagination_button_image = getImageFileFromUiUtils_AboutVrct("poster_showcase_pagination_button.png")
        self.image_file.POSTER_SHOWCASE_WORLD_PAGINATION_BUTTON = SimpleNamespace(
            img = poster_showcase_pagination_button_image,
            width = calculateUiSize(
                default_size = int(poster_showcase_pagination_button_image.width / IMAGE_STANDARD_SCALING),
                scaling_float=self.SCALING_FLOAT,
                is_allowed_odd=True,
            ),
            height = calculateUiSize(
                default_size = int(poster_showcase_pagination_button_image.height / IMAGE_STANDARD_SCALING),
                scaling_float=self.SCALING_FLOAT,
                is_allowed_odd=True,
            ),
        )


        poster_showcase_pagination_button_chato_image = getImageFileFromUiUtils_AboutVrct("poster_showcase_pagination_button_chato.png")
        self.image_file.POSTER_SHOWCASE_WORLD_PAGINATION_BUTTON_CHATO = SimpleNamespace(
            img = poster_showcase_pagination_button_chato_image,
            width = calculateUiSize(
                default_size = int(poster_showcase_pagination_button_chato_image.width / IMAGE_STANDARD_SCALING),
                scaling_float=self.SCALING_FLOAT,
                is_allowed_odd=True,
            ),
            height = calculateUiSize(
                default_size = int(poster_showcase_pagination_button_chato_image.height / IMAGE_STANDARD_SCALING),
                scaling_float=self.SCALING_FLOAT,
                is_allowed_odd=True,
            ),
        )




    def _calculateUiSize(self, default_size, is_allowed_odd:bool=True, is_zero_allowed:bool=False):
        size = calculateUiSize(default_size, self.SCALING_FLOAT, is_allowed_odd, is_zero_allowed)
        return size


    def embedImageCTkLabel(self, parent_frame, image_file_name, image_scaling=IMAGE_STANDARD_SCALING, directly_type:str=None, fg_color:str="transparent", anchor:str="w"):

        img = getImageFileFromUiUtils_AboutVrct(image_file_name, directly_type)

        image_width = calculateUiSize(
            default_size = int(img.width / image_scaling),
            scaling_float=self.SCALING_FLOAT,
            is_allowed_odd=True,
        )
        image_height = calculateUiSize(
            default_size = int(img.height / image_scaling),
            scaling_float=self.SCALING_FLOAT,
            is_allowed_odd=True,
        )

        img_label = CTkLabel(
            parent_frame,
            text=None,
            corner_radius=0,
            height=image_height,
            fg_color=fg_color,
            anchor=anchor,
            image=CTkImage((img), size=(image_width, image_height))
        )

        return img_label

    def embedImageButtonCTkLabel(self, parent_frame, image_file_name, callback, image_scaling=IMAGE_STANDARD_SCALING, directly_type:str=None, fg_color:str=None, hovered_color:str=None, clicked_color:str=None, anchor:str="w", corner_radius:int=0):

        fg_color = self.ctm.ABOUT_VRCT_BG if fg_color is None else fg_color

        if hovered_color is None:
            hovered_color = self.ctm.ABOUT_VRCT_BUTTON_HOVERED_BG_COLOR
        if clicked_color is None:
            clicked_color = self.ctm.ABOUT_VRCT_BUTTON_CLICKED_BG_COLOR

        img_label_frame = CTkFrame(parent_frame, fg_color=fg_color, corner_radius=corner_radius, width=0, height=0)

        img_label = self.embedImageCTkLabel(img_label_frame, image_file_name, image_scaling, directly_type, fg_color, anchor)

        img_label_frame.configure(cursor="hand2")
        img_label.configure(cursor="hand2")
        img_label._canvas.configure(cursor="hand2")
        bindButtonFunctionAndColor(
            target_widgets=[img_label_frame, img_label],
            enter_color=hovered_color,
            leave_color=fg_color,
            clicked_color=clicked_color,
            buttonReleasedFunction=callback,
        )

        img_label.grid()
        img_label_frame.img_label = img_label

        return img_label_frame


    @staticmethod
    def dupTuple(value):
        return (value, value)