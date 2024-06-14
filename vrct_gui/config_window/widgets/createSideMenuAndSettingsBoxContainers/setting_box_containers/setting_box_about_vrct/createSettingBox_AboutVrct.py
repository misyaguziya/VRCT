from random import randint
from types import SimpleNamespace
from customtkinter import CTkFrame, CTkLabel, CTkImage, CTkFont

from utils import callFunctionIfCallable, splitList
from ......ui_utils import bindButtonFunctionAndColor, animateRotation, bindEnterAndLeaveFunction
from .about_vrct_store import poster_showcase_worlds_settings

def createSettingBox_AboutVrct(setting_box_wrapper, config_window, settings, view_variable):
    setting_box_wrapper.grid_columnconfigure(0, weight=1, minsize=settings.uism.MAIN_AREA_MIN_WIDTH)
    about_vrct_uism = settings.about_vrct.uism
    ABOUT_VRCT_BG = settings.ctm.ABOUT_VRCT_BG


    # For padding left. without this, setting_box_wrapper's bg shows...
    about_vrct_container_wrapper = CTkFrame(setting_box_wrapper, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
    about_vrct_container_wrapper.grid(column=0, row=0, padx=0, pady=0, sticky="nsew")
    about_vrct_container_wrapper.grid_columnconfigure(0, weight=1)


    about_vrct_container = CTkFrame(about_vrct_container_wrapper, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
    about_vrct_container.grid(column=0, row=0, padx=about_vrct_uism.ABOUT_VRCT_CONTAINER_LEFT_PADX, pady=0, sticky="nsew")
    about_vrct_container.grid_columnconfigure(0, weight=1)


    def createSectionContainer(section_row, section_title_image_file_name:str=None, section_bottom_padding:int=0, section_title_bottom_padding:int=0):
        section_container = CTkFrame(about_vrct_container, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
        section_container.grid(column=0, row=section_row, padx=0, pady=(0, section_bottom_padding), sticky="nsew")
        section_container.grid_columnconfigure(0, weight=1)

        contents_row=0
        if section_title_image_file_name is not None:
            section_title_frame = settings.about_vrct.embedImageCTkLabel(section_container, section_title_image_file_name)
            section_title_frame.grid(column=0, row=contents_row, padx=0, pady=(0,section_title_bottom_padding), sticky="nw")
            contents_row = 1



        section_contents_wrapper = CTkFrame(section_container, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
        section_contents_wrapper.grid(column=0, row=contents_row, padx=0, pady=0, sticky="nsew")
        section_contents_wrapper.grid_columnconfigure(0, weight=1)

        return (section_container, section_contents_wrapper)



    def createImageButtonRows(parent_frame, image_buttons_settings:list, bottom_pady, directly_type:str=None, corner_radius:int=0, ipadx:int=0, ipady:int=0):
        button_row=0
        setting_length = len(image_buttons_settings)
        for index, each_setting in enumerate(image_buttons_settings):
            each_button = settings.about_vrct.embedImageButtonCTkLabel(
                parent_frame=parent_frame,
                image_file_name=each_setting["image_file_name"],
                callback=each_setting.get("callback", None),
                directly_type=directly_type,
                corner_radius=corner_radius,
                no_bind=each_setting.get("no_bind", False),
            )
            each_button.grid(column=0, row=button_row, padx=0, pady=(0, bottom_pady), sticky="nsew")
            each_button.img_label.grid(padx=ipadx, pady=ipady, sticky="nsew")
            if index == setting_length-1:
                each_button.grid(pady=0)
            button_row+=1

    def createContactButton(parent_frame, image_file_name, callback_arg, fg_color=ABOUT_VRCT_BG):
        frame = settings.about_vrct.embedImageButtonCTkLabel(
            parent_frame=parent_frame,
            image_file_name=image_file_name,
            callback=lambda _e: callFunctionIfCallable(view_variable.CALLBACK_OPEN_WEBPAGE_ABOUT_VRCT, callback_arg),
            fg_color=fg_color,
            hovered_color=fg_color,
            clicked_color=fg_color,
        )
        return frame

    def createTellUsButton(parent_frame, image_file_name, callback):
        tell_us_button_frame = settings.about_vrct.embedImageButtonCTkLabel(
            parent_frame=parent_frame,
            image_file_name=image_file_name,
            callback=callback,
            corner_radius=about_vrct_uism.TELL_US_BUTTON_CORNER_RADIUS,
        )
        tell_us_button_frame.img_label.grid(padx=about_vrct_uism.TELL_US_BUTTON_PADX, pady=about_vrct_uism.TELL_US_BUTTON_PADY, sticky="nsew")

        tell_us_button_frame.configure(border_width=about_vrct_uism.TELL_US_BUTTON_BORDER_WIDTH, border_color=settings.ctm.ABOUT_VRCT_TELL_US_BUTTON_BORDER_COLOR)

        return tell_us_button_frame




    section_row=0
    # The Developers ----------------------------------
    _the_developers, the_developers_contents_wrapper = createSectionContainer(
        section_row=section_row,
        section_title_image_file_name="dev_section_title.png",
        section_bottom_padding=about_vrct_uism.SECTION_BOTTOM_PADY,
        section_title_bottom_padding=about_vrct_uism.THE_DEVELOPERS_SECTION_TITLE_BOTTOM_PADY
    )

    dev_misya_label = settings.about_vrct.embedImageCTkLabel(the_developers_contents_wrapper, "dev_misya.png")
    dev_misya_label.grid(column=0, row=0, padx=0, pady=0, sticky="nsw")

    dev_misya_x = createContactButton(
        parent_frame=dev_misya_label,
        image_file_name="dev_x_icon.png",
        callback_arg="X_MISYA",
        fg_color=settings.ctm.ABOUT_VRCT_DEV_BG
    )
    dev_misya_x.place(x=about_vrct_uism.DEVS_MISYA_X_X, y=about_vrct_uism.DEVS_CONTACTS_Y1, anchor="nw")

    dev_misya_github = createContactButton(
        parent_frame=dev_misya_label,
        image_file_name="dev_github_icon.png",
        callback_arg="GITHUB_MISYA",
        fg_color=settings.ctm.ABOUT_VRCT_DEV_BG
    )
    dev_misya_github.place(x=about_vrct_uism.DEVS_MISYA_GITHUB_X, y=about_vrct_uism.DEVS_CONTACTS_Y1, anchor="nw")



    dev_shiina_label = settings.about_vrct.embedImageCTkLabel(the_developers_contents_wrapper, "dev_shiina.png")
    dev_shiina_label.grid(column=1, row=0, padx=0, pady=0, sticky="nse")

    dev_shiina_x = createContactButton(
        parent_frame=dev_shiina_label,
        image_file_name="dev_x_icon.png",
        callback_arg="X_SHIINA",
        fg_color=settings.ctm.ABOUT_VRCT_DEV_BG
    )
    dev_shiina_x.place(x=about_vrct_uism.DEVS_SHIINA_X_X, y=about_vrct_uism.DEVS_CONTACTS_Y1, anchor="nw")


    section_row+=1
    # Project Links And Logo ----------------------------------
    _project_links_and_logo, project_links_and_logo_contents_wrapper = createSectionContainer(
        section_bottom_padding=about_vrct_uism.PROJECT_LINKS_SECTION_BOTTOM_PADDING,
        section_row=section_row,
    )

    project_links_and_logo_wrapper = CTkFrame(project_links_and_logo_contents_wrapper, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
    project_links_and_logo_wrapper.grid(column=0, row=0, padx=about_vrct_uism.PROJECT_LINK_CONTENTS_PADX, pady=0, sticky="nsew")
    project_links_and_logo_wrapper.grid_columnconfigure(1, weight=1)


    vrct_logo_label = settings.about_vrct.embedImageCTkLabel(project_links_and_logo_wrapper, "vrct_logo_for_about_vrct.png")
    vrct_logo_label.grid(column=0, row=0, padx=0, pady=0, sticky="nsw")


    project_links_wrapper = CTkFrame(project_links_and_logo_wrapper, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
    project_links_wrapper.grid(column=2, row=0, padx=0, pady=0, sticky="nse")

    project_link_settings = [
        {
            "image_file_name": "project_link_booth.png",
            "callback": lambda _e: callFunctionIfCallable(view_variable.CALLBACK_OPEN_WEBPAGE_ABOUT_VRCT, "BOOTH")
        },
        {
            "image_file_name": "project_link_documents.png",
            "callback": lambda _e: callFunctionIfCallable(view_variable.CALLBACK_OPEN_WEBPAGE_ABOUT_VRCT, "VRCT_DOCUMENTS")
        },
        {
            "image_file_name": "project_link_vrct_github.png",
            "callback": lambda _e: callFunctionIfCallable(view_variable.CALLBACK_OPEN_WEBPAGE_ABOUT_VRCT, "VRCT_GITHUB")
        },
        {
            "image_file_name": "project_link_contact_us.png",
            "callback": lambda _e: callFunctionIfCallable(view_variable.CALLBACK_OPEN_WEBPAGE_ABOUT_VRCT, "CONTACT_US")
        },
    ]

    createImageButtonRows(
        parent_frame=project_links_wrapper,
        image_buttons_settings=project_link_settings,
        bottom_pady=about_vrct_uism.PROJECT_LINK_BOTTOM_PADY,
        corner_radius=about_vrct_uism.PROJECT_LINK_CORNER_RADIUS,
        ipadx=about_vrct_uism.PROJECT_LINK_ITEM_IPADX,
        ipady=about_vrct_uism.PROJECT_LINK_ITEM_IPADY,
    )






    section_row+=1
    # Contributors ----------------------------------
    _contributors, contributors_contents_wrapper = createSectionContainer(
        section_row=section_row,
        section_title_image_file_name="contributors_section_title.png",
        section_bottom_padding=about_vrct_uism.SECTION_BOTTOM_PADY,
        section_title_bottom_padding=about_vrct_uism.CONTRIBUTORS_SECTION_TITLE_BOTTOM_PADY
    )

    contributors_members = settings.about_vrct.embedImageCTkLabel(contributors_contents_wrapper, "contributors_members.png")
    contributors_members.grid(column=0, row=0, padx=0, pady=0, sticky="nsew")



    # done_san
    contributors_done_san_x = createContactButton(
        parent_frame=contributors_members,
        image_file_name="contributors_x_icon.png",
        callback_arg="X_DONE_SAN",
    )
    contributors_done_san_x.place(x=about_vrct_uism.CONTRIBUTORS_DONE_SAN_X_X, y=about_vrct_uism.CONTRIBUTORS_CONTACTS_Y1, anchor="nw")

    # IYA
    contributors_iya_x = createContactButton(
        parent_frame=contributors_members,
        image_file_name="contributors_x_icon.png",
        callback_arg="X_IYA",
    )
    contributors_iya_x.place(x=about_vrct_uism.CONTRIBUTORS_IYA_X_X, y=about_vrct_uism.CONTRIBUTORS_CONTACTS_Y1, anchor="nw")

    # RERA
    contributors_rera_x = createContactButton(
        parent_frame=contributors_members,
        image_file_name="contributors_x_icon.png",
        callback_arg="X_RERA",
    )
    contributors_rera_x.place(x=about_vrct_uism.CONTRIBUTORS_RERA_X_X, y=about_vrct_uism.CONTRIBUTORS_CONTACTS_Y1, anchor="nw")

    contributors_rera_github = createContactButton(
        parent_frame=contributors_members,
        image_file_name="contributors_github_icon.png",
        callback_arg="GITHUB_RERA",
    )
    contributors_rera_github.place(x=about_vrct_uism.CONTRIBUTORS_RERA_GITHUB_X, y=about_vrct_uism.CONTRIBUTORS_CONTACTS_Y1, anchor="nw")


    # POPOSUKE
    contributors_poposuke_x = createContactButton(
        parent_frame=contributors_members,
        image_file_name="contributors_x_icon.png",
        callback_arg="X_POPOSUKE",
    )
    contributors_poposuke_x.place(x=about_vrct_uism.CONTRIBUTORS_POPOSUKE_X_X, y=about_vrct_uism.CONTRIBUTORS_CONTACTS_Y2, anchor="nw")

    # KUMAGUMA
    contributors_kumaguma_x = createContactButton(
        parent_frame=contributors_members,
        image_file_name="contributors_x_icon.png",
        callback_arg="X_KUMAGUMA",
    )
    contributors_kumaguma_x.place(x=about_vrct_uism.CONTRIBUTORS_KUMAGUMA_X_X, y=about_vrct_uism.CONTRIBUTORS_CONTACTS_Y2, anchor="nw")






    section_row+=1
    # Localization ----------------------------------
    _localization, localization_contents_wrapper = createSectionContainer(
        section_row=section_row,
        section_title_image_file_name="localization_title.png",
        section_bottom_padding=about_vrct_uism.SECTION_BOTTOM_PADY,
        section_title_bottom_padding=about_vrct_uism.LOCALIZATION_TITLE_BOTTOM_PADY
    )

    localization_members = settings.about_vrct.embedImageCTkLabel(localization_contents_wrapper, "localization_members.png")
    localization_members.grid(column=0, row=0, padx=0, pady=0, sticky="nsew")



    section_row+=1
    # Special Thanks & Supporters ----------------------------------
    _special_thanks, special_thanks_contents_wrapper = createSectionContainer(
        section_row=section_row,
        section_title_image_file_name="special_thanks_section_title.png",
        section_bottom_padding=about_vrct_uism.SECTION_BOTTOM_PADY,
        section_title_bottom_padding=about_vrct_uism.SPECIAL_THANKS_SECTION_TITLE_BOTTOM_PADY
    )

    special_thanks_members = settings.about_vrct.embedImageCTkLabel(special_thanks_contents_wrapper, "special_thanks_members.png")
    special_thanks_members.grid(column=0, row=0, padx=0, pady=(0,about_vrct_uism.SPECIAL_THANKS_MEMBERS_BOTTOM_PADY), sticky="nsew")

    special_thanks_message = settings.about_vrct.embedImageCTkLabel(special_thanks_contents_wrapper, settings.about_vrct.image_file.SPECIAL_THANKS_MESSAGE)
    special_thanks_message.grid(column=0, row=1, padx=0, pady=(0,about_vrct_uism.SPECIAL_THANKS_MESSAGE_BOTTOM_PADY), sticky="nsew")

    special_thanks_message_and_you = settings.about_vrct.embedImageCTkLabel(special_thanks_contents_wrapper, "special_thanks_message_and_you.png")
    special_thanks_message_and_you.grid(column=0, row=2, padx=0, pady=(0,about_vrct_uism.SPECIAL_THANKS_MESSAGE_AND_YOU_BOTTOM_PADY), sticky="nsw")

    special_thanks_tell_us_message = createTellUsButton(
        parent_frame=special_thanks_contents_wrapper,
        image_file_name=settings.about_vrct.image_file.SPECIAL_THANKS_TELL_US_MESSAGE,
        callback=lambda _e: callFunctionIfCallable(view_variable.CALLBACK_OPEN_WEBPAGE_ABOUT_VRCT, "SUPPORTER_REGISTRATION"),
    )
    special_thanks_tell_us_message.grid(column=0, row=3)




    section_row+=1
    # Special Thanks & Supporters ----------------------------------
    _poster_showcase, poster_showcase_contents_wrapper = createSectionContainer(
        section_row=section_row,
        section_title_image_file_name="poster_showcase_section_title.png",
        section_bottom_padding=about_vrct_uism.SECTION_BOTTOM_PADY,
        section_title_bottom_padding=about_vrct_uism.POSTER_SHOWCASE_SECTION_TITLE_BOTTOM_PADY
    )

    poster_showcase_worlds_wrapper = CTkFrame(poster_showcase_contents_wrapper, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
    poster_showcase_worlds_wrapper.grid(column=0, row=0, padx=0, pady=0, sticky="nsew")
    poster_showcase_worlds_wrapper.grid_columnconfigure(0, weight=1)


    poster_showcase_worlds = CTkFrame(poster_showcase_worlds_wrapper, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
    poster_showcase_worlds.grid(column=0, row=0, padx=0, pady=(0,about_vrct_uism.POSTER_SHOWCASE_WORLD_BOTTOM_PADY), sticky="nsew")
    poster_showcase_worlds.grid_columnconfigure(0, weight=1)



    compounded_poster_showcase_worlds_list = []
    for each_author_settings in poster_showcase_worlds_settings:
        for data in each_author_settings["data"]:
            if data["x_post_num"] is None:
                append_settings = {
                    "image_file_name": data["image_file_name"],
                    "no_bind": True,
                }
            else:
                x_post_num = data["x_post_num"]
                callback = lambda _e,arg=x_post_num: view_variable.CALLBACK_OPEN_WEBPAGE_ABOUT_VRCT("X_SHIINA_POSTER_SHOWCASE_POST", arg)
                append_settings = {
                    "image_file_name": data["image_file_name"],
                    "callback": callback,
                }
            compounded_poster_showcase_worlds_list.append(append_settings)

    result = splitList(compounded_poster_showcase_worlds_list, 8)
    poster_showcase_worlds_frame_list = []
    for split_poster_showcase_worlds_settings in result:
        poster_showcase_worlds_frame = CTkFrame(poster_showcase_worlds_wrapper, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
        poster_showcase_worlds_frame.grid_columnconfigure(0, weight=1)

        createImageButtonRows(
            parent_frame=poster_showcase_worlds_frame,
            image_buttons_settings=split_poster_showcase_worlds_settings,
            bottom_pady=about_vrct_uism.POSTER_SHOWCASE_WORLD_ITEM_BOTTOM_PADY,
            directly_type="showcased_worlds",
            corner_radius=about_vrct_uism.POSTER_SHOWCASE_WORLD_CORNER_RADIUS,
            ipadx=about_vrct_uism.POSTER_SHOWCASE_WORLD_ITEM_IPADX,
            ipady=about_vrct_uism.POSTER_SHOWCASE_WORLD_ITEM_IPADY,
        )

        poster_showcase_worlds_frame_list.append(poster_showcase_worlds_frame)


    pagination_button_settings = settings.about_vrct.image_file.POSTER_SHOWCASE_WORLD_PAGINATION_BUTTON

    def defineAngles(index):
        start_angle = 0
        goal_angle = 90
        if index == 0:
            start_angle = 0
            goal_angle = 90
        elif index == 1:
            start_angle = 90
            goal_angle = 180
        elif index == 2:
            start_angle = 180
            goal_angle = 270
        elif index == 3:
            start_angle = 270
            goal_angle = 360
        return(start_angle, goal_angle)

    def toNextPagePosterShowcase():
        current_function_index = view_variable.CALLBACK_ABOUT_VRCT_POSTER_SHOWCASE_CURRENT_PAGE_NUM
        view_variable.CALLBACK_ABOUT_VRCT_CHANGE_POSTER_SHOWCASE_WORLD_LIST=None
        poster_showcase_worlds_frame_list[current_function_index].grid_remove()
        pre_function_index = current_function_index
        current_function_index = (current_function_index + 1) % len(poster_showcase_worlds_frame_list)
        poster_showcase_worlds_frame_list[current_function_index].grid(column=0, row=0, padx=0, pady=(0,about_vrct_uism.POSTER_SHOWCASE_WORLD_BOTTOM_PADY), sticky="nsew")
        view_variable.CALLBACK_ABOUT_VRCT_POSTER_SHOWCASE_CURRENT_PAGE_NUM = current_function_index

        start_angle, goal_angle = defineAngles(pre_function_index)

        animateRotation(
            tk_root=config_window,
            img_frame=config_window.poster_showcase_pagination_button.img_label,
            img=pagination_button_settings.img,
            img_width=pagination_button_settings.width,
            img_height=pagination_button_settings.height,
            start_angle=start_angle,
            goal_angle=goal_angle,
            duration=0.5,
        )

        view_variable.CALLBACK_ABOUT_VRCT_CHANGE_POSTER_SHOWCASE_WORLD_LIST=toNextPagePosterShowcase

    # Initialize
    view_variable.CALLBACK_ABOUT_VRCT_CHANGE_POSTER_SHOWCASE_WORLD_LIST=toNextPagePosterShowcase

    view_variable.CALLBACK_ABOUT_VRCT_POSTER_SHOWCASE_CURRENT_PAGE_NUM = randint(0, len(poster_showcase_worlds_frame_list)-1)

    start_angle, _goal_angle = defineAngles(view_variable.CALLBACK_ABOUT_VRCT_POSTER_SHOWCASE_CURRENT_PAGE_NUM)

    poster_showcase_worlds_frame_list[view_variable.CALLBACK_ABOUT_VRCT_POSTER_SHOWCASE_CURRENT_PAGE_NUM].grid(column=0, row=0, padx=0, pady=(0,about_vrct_uism.POSTER_SHOWCASE_WORLD_BOTTOM_PADY), sticky="nsew")

    poster_showcase_worlds_wrapper.grid_rowconfigure(1, weight=1)

    poster_showcase_pagination_button_wrapper = CTkFrame(poster_showcase_worlds_wrapper, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
    poster_showcase_pagination_button_wrapper.grid(column=0, row=2, padx=0, pady=(0, about_vrct_uism.POSTER_SHOWCASE_WORLD_PAGINATION_BUTTON_BOTTOM_PADY), sticky="nsew")


    poster_showcase_pagination_button_wrapper.grid_columnconfigure((0,2), weight=1)
    config_window.poster_showcase_pagination_button = settings.about_vrct.embedImageButtonCTkLabel(
        parent_frame=poster_showcase_pagination_button_wrapper,
        image_file_name="poster_showcase_pagination_button.png",
        callback=lambda _e: callFunctionIfCallable(view_variable.CALLBACK_ABOUT_VRCT_CHANGE_POSTER_SHOWCASE_WORLD_LIST),
        hovered_color="transparent",
        clicked_color="transparent",
        rotate_angle=-start_angle # for clockwise angle, put negative "-"
    )
    config_window.poster_showcase_pagination_button.grid(column=1, row=0, padx=0, pady=0, sticky="nsew")


    # poster_showcase_pagination_button_wrapper.grid_columnconfigure((0,2), weight=1)
    poster_showcase_pagination_button_chato = settings.about_vrct.embedImageButtonCTkLabel(
        parent_frame=poster_showcase_pagination_button_wrapper,
        image_file_name="poster_showcase_pagination_button_chato.png",
        callback=lambda _e: callFunctionIfCallable(view_variable.CALLBACK_ABOUT_VRCT_CHANGE_POSTER_SHOWCASE_WORLD_LIST),
        hovered_color="transparent",
        clicked_color="transparent",
    )
    poster_showcase_pagination_button_chato.place(relx=0.502, rely=0.51, anchor="center")

    pagination_button_chato_settings = settings.about_vrct.image_file.POSTER_SHOWCASE_WORLD_PAGINATION_BUTTON_CHATO

    def rotateChatoAnimation():
        view_variable.CALLBACK_ABOUT_VRCT_CHANGE_POSTER_SHOWCASE_BUTTON_HOVERED = None

        animateRotation(
            tk_root=config_window,
            img_frame=poster_showcase_pagination_button_chato.img_label,
            img=pagination_button_chato_settings.img,
            img_width=pagination_button_chato_settings.width,
            img_height=pagination_button_chato_settings.height,
            start_angle=0,
            goal_angle=360,
            duration=0.5,
        )
        view_variable.CALLBACK_ABOUT_VRCT_CHANGE_POSTER_SHOWCASE_BUTTON_HOVERED = rotateChatoAnimation


    view_variable.CALLBACK_ABOUT_VRCT_CHANGE_POSTER_SHOWCASE_BUTTON_HOVERED = rotateChatoAnimation

    bindEnterAndLeaveFunction(
        target_widgets=[config_window.poster_showcase_pagination_button.img_label,poster_showcase_pagination_button_chato.img_label],
        enterFunction=lambda _e: callFunctionIfCallable(view_variable.CALLBACK_ABOUT_VRCT_CHANGE_POSTER_SHOWCASE_BUTTON_HOVERED),
        leaveFunction=None,
    )




    poster_container = CTkFrame(poster_showcase_contents_wrapper, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
    poster_container.grid(column=1, row=0, padx=0, pady=0, sticky="nsew")
    poster_container.grid_columnconfigure(1, weight=1)


    poster_images_wrapper = CTkFrame(poster_container, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
    poster_images_wrapper.grid(column=0, row=0, padx=0, pady=(0,about_vrct_uism.POSTER_SHOWCASE_POSTER_IMAGES_BOTTOM_PADY), sticky="nsew")
    poster_images_wrapper.grid_columnconfigure(1, weight=1)




    poster_image_arrow_left = settings.about_vrct.embedImageButtonCTkLabel(poster_images_wrapper, "arrow_left.png", lambda _e: callFunctionIfCallable(view_variable.CALLBACK_ABOUT_VRCT_POSTER_PREV_BUTTON))
    poster_image_arrow_left.grid(column=0, row=0, padx=0, pady=0, sticky="nsew")
    poster_image_arrow_left.configure(corner_radius=about_vrct_uism.POSTER_CHANGE_BUTTON_CORNER_RADIUS)

    bindButtonFunctionAndColor(
        target_widgets=[poster_image_arrow_left],
        enter_color=settings.ctm.ABOUT_VRCT_BUTTON_HOVERED_BG_COLOR,
        leave_color=ABOUT_VRCT_BG,
        clicked_color=settings.ctm.ABOUT_VRCT_BUTTON_CLICKED_BG_COLOR,
        buttonReleasedFunction=None,
    )


    poster_image_frame_settings_list = [
        {
            "file_name": "iya_vrct_poster_ja.png",
            "poster_type": "poster",
        },
        {
            "file_name": "iya_vrct_poster_en.png",
            "poster_type": "poster",
        },
        {
            "file_name": "iya_vrct_poster_cn.png",
            "poster_type": "poster",
        },
        {
            "file_name": "iya_vrct_poster_ko.png",
            "poster_type": "poster",
        },
        {
            "file_name": "iya_vrct_manga_ja.png",
            "poster_type": "manga",
        },
        {
            "file_name": "iya_vrct_manga_en.png",
            "poster_type": "manga",
        },
        {
            "file_name": "iya_vrct_manga_ko.png",
            "poster_type": "manga",
        },
    ]

    poster_frame_list = []
    for poster_frame_settings in poster_image_frame_settings_list:
        poster_frame = settings.about_vrct.embedImageCTkLabel(poster_images_wrapper, poster_frame_settings["file_name"], directly_type="vrct_posters")
        poster_frame_list.append(poster_frame)




    poster_images_authors_wrapper = CTkFrame(poster_container, fg_color=ABOUT_VRCT_BG, corner_radius=0, width=0, height=0)
    poster_images_authors_wrapper.grid(column=0, row=1, padx=0, pady=0, sticky="nsew")

    config_window.poster_images_authors = settings.about_vrct.embedImageCTkLabel(poster_images_authors_wrapper, settings.about_vrct.image_file.POSTER_IMAGES_AUTHOR)
    config_window.poster_images_authors_m = settings.about_vrct.embedImageCTkLabel(poster_images_authors_wrapper, settings.about_vrct.image_file.POSTER_IMAGES_AUTHOR_M)



    def toPrevPagePosterImage():
        current_function_index = view_variable.CALLBACK_ABOUT_VRCT_POSTER_IMAGE_CURRENT_PAGE_NUM
        view_variable.CALLBACK_ABOUT_VRCT_POSTER_PREV_BUTTON=None
        view_variable.CALLBACK_ABOUT_VRCT_POSTER_NEXT_BUTTON=None
        poster_frame_list[current_function_index].grid_remove()
        current_function_index = (current_function_index - 1) % len(poster_frame_list)
        poster_frame_list[current_function_index].grid(column=1, row=0, padx=0, pady=0, sticky="nsew")
        view_variable.CALLBACK_ABOUT_VRCT_POSTER_IMAGE_CURRENT_PAGE_NUM = current_function_index

        if poster_image_frame_settings_list[current_function_index]["poster_type"] == "poster":
            config_window.poster_images_authors_m.grid_remove()
            config_window.poster_images_authors.grid(column=0, row=0, padx=0, pady=0, sticky="nsew")
        elif poster_image_frame_settings_list[current_function_index]["poster_type"] == "manga":
            config_window.poster_images_authors.grid_remove()
            config_window.poster_images_authors_m.grid(column=0, row=0, padx=0, pady=0, sticky="nsew")

        view_variable.CALLBACK_ABOUT_VRCT_POSTER_PREV_BUTTON=toPrevPagePosterImage
        view_variable.CALLBACK_ABOUT_VRCT_POSTER_NEXT_BUTTON=toNextPagePosterImage




    def toNextPagePosterImage():
        current_function_index = view_variable.CALLBACK_ABOUT_VRCT_POSTER_IMAGE_CURRENT_PAGE_NUM
        view_variable.CALLBACK_ABOUT_VRCT_POSTER_PREV_BUTTON=None
        view_variable.CALLBACK_ABOUT_VRCT_POSTER_NEXT_BUTTON=None
        poster_frame_list[current_function_index].grid_remove()
        current_function_index = (current_function_index + 1) % len(poster_frame_list)
        poster_frame_list[current_function_index].grid(column=1, row=0, padx=0, pady=0, sticky="nsew")
        view_variable.CALLBACK_ABOUT_VRCT_POSTER_IMAGE_CURRENT_PAGE_NUM = current_function_index

        if poster_image_frame_settings_list[current_function_index]["poster_type"] == "poster":
            config_window.poster_images_authors_m.grid_remove()
            config_window.poster_images_authors.grid(column=0, row=0, padx=0, pady=0, sticky="nsew")
        elif poster_image_frame_settings_list[current_function_index]["poster_type"] == "manga":
            config_window.poster_images_authors.grid_remove()
            config_window.poster_images_authors_m.grid(column=0, row=0, padx=0, pady=0, sticky="nsew")


        view_variable.CALLBACK_ABOUT_VRCT_POSTER_PREV_BUTTON=toPrevPagePosterImage
        view_variable.CALLBACK_ABOUT_VRCT_POSTER_NEXT_BUTTON=toNextPagePosterImage



    # Initialize
    view_variable.CALLBACK_ABOUT_VRCT_POSTER_PREV_BUTTON=toPrevPagePosterImage
    view_variable.CALLBACK_ABOUT_VRCT_POSTER_NEXT_BUTTON=toNextPagePosterImage

    config_window.poster_images_authors.grid(column=0, row=0, padx=0, pady=0, sticky="nsew")

    poster_frame_list[0].grid(column=1, row=0, padx=0, pady=0, sticky="nsew")




    poster_image_arrow_right = settings.about_vrct.embedImageButtonCTkLabel(poster_images_wrapper, "arrow_right.png", lambda _e: callFunctionIfCallable(view_variable.CALLBACK_ABOUT_VRCT_POSTER_NEXT_BUTTON))
    poster_image_arrow_right.grid(column=2, row=0, padx=0, pady=0, sticky="nsew")
    poster_image_arrow_right.configure(corner_radius=about_vrct_uism.POSTER_CHANGE_BUTTON_CORNER_RADIUS)


    bindButtonFunctionAndColor(
        target_widgets=[poster_image_arrow_right],
        enter_color=settings.ctm.ABOUT_VRCT_BUTTON_HOVERED_BG_COLOR,
        leave_color=ABOUT_VRCT_BG,
        clicked_color=settings.ctm.ABOUT_VRCT_BUTTON_CLICKED_BG_COLOR,
        buttonReleasedFunction=None,
    )








    poster_tell_us_message = createTellUsButton(
        parent_frame=poster_showcase_contents_wrapper,
        image_file_name=settings.about_vrct.image_file.POSTER_TELL_US_MESSAGE,
        callback=lambda _e: callFunctionIfCallable(view_variable.CALLBACK_OPEN_WEBPAGE_ABOUT_VRCT, "POSTER_CONTACT_US"),
    )
    poster_tell_us_message.grid(column=0, row=1, columnspan=2, padx=0, pady=(about_vrct_uism.POSTER_TELL_US_MESSAGE_TOP_PADY,0), sticky="nse")











    section_row+=1
    # VRChat disclaimer ----------------------------------
    vrchat_disclaimer, vrchat_disclaimer_contents_wrapper = createSectionContainer(
        section_row=section_row,
    )


    vrchat_disclaimer_label = settings.about_vrct.embedImageCTkLabel(vrchat_disclaimer_contents_wrapper, "vrchat_disclaimer.png")
    vrchat_disclaimer_label.grid(column=0, row=0, padx=0, pady=about_vrct_uism.VRCHAT_DISCLAIMER_SECTION_PADY, sticky="nsew")