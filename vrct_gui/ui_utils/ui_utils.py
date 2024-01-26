from os import path as os_path
from PIL.Image import open as Image_open, LANCZOS
from time import sleep

from customtkinter import CTkFrame, CTkLabel, CTkImage, CTkFont

def getImagePath(file_name):
    # root\img\file_name
    return os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "img", file_name)

def getImageFileFromUiUtils(file_name):
    # root\img\file_name
    img = Image_open(os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "img", file_name))
    return img

def openImageKeepAspectRatio(image_file, desired_width):
    wpercent = (desired_width/float(image_file.size[0]))
    hsize = int((float(image_file.size[1])*float(wpercent)))
    img = image_file.resize((desired_width,hsize), LANCZOS)
    return (img, desired_width, hsize)

def retag(tag, *args):
    for widget in args:
        widget.bindtags((tag,) + widget.bindtags())


def getLatestWidth(target_widget):
    target_widget.update_idletasks()
    return target_widget.winfo_width()

def getLatestHeight(target_widget):
    target_widget.update_idletasks()
    return target_widget.winfo_height()

def getLongestText(text_list:list):
    max_length = 0
    longest_text = ""

    for text in text_list:
        if len(text) > max_length:
            max_length = len(text)
            longest_text = text
    return longest_text

def getLongestText_Dict(text_dict:dict):
    max_length = 0
    longest_text = ""

    for key, text in text_dict.items():
        if len(text) > max_length:
            max_length = len(text)
            longest_text = text

    return longest_text

def calculateUiSize(default_size, scaling_float, is_allowed_odd:bool=False, is_zero_allowed:bool=False):
        size = int(default_size * scaling_float)
        size += 1 if not is_allowed_odd and size % 2 != 0 else 0
        if size <= 0:
            size = 0 if is_zero_allowed else 1

        return size

def bindEnterAndLeaveColor(target_widgets, enter_color, leave_color):
    for target_widget in target_widgets:
        target_widget.bind("<Enter>", lambda e, widgets=target_widgets: [w.configure(fg_color=enter_color) for w in widgets], "+")
        target_widget.bind("<Leave>", lambda e, widgets=target_widgets: [w.configure(fg_color=leave_color) for w in widgets], "+")


def bindButtonPressColor(target_widgets, clicked_color, released_color):
    for target_widget in target_widgets:
        target_widget.bind("<ButtonPress>", lambda e, widgets=target_widgets: [w.configure(fg_color=clicked_color) for w in widgets], "+")
        target_widget.bind("<ButtonRelease>", lambda e, widgets=target_widgets: [w.configure(fg_color=released_color) for w in widgets], "+")

def bindEnterAndLeaveFunction(target_widgets, enterFunction, leaveFunction):
    for target_widget in target_widgets:
        target_widget.bind("<Enter>", enterFunction, "+")
        target_widget.bind("<Leave>", leaveFunction, "+")

def bindButtonPressFunction(target_widgets, buttonPressedFunction):
    for target_widget in target_widgets:
        target_widget.bind("<ButtonPress>", buttonPressedFunction, "+")

def bindButtonReleaseFunction(target_widgets, buttonReleasedFunction):
    for target_widget in target_widgets:
        target_widget.bind("<ButtonRelease>", buttonReleasedFunction, "+")

def bindButtonPressAndReleaseFunction(target_widgets, buttonPressedFunction, buttonReleasedFunction):
    for target_widget in target_widgets:
        target_widget.bind("<ButtonPress>", buttonPressedFunction, "+")
        target_widget.bind("<ButtonRelease>", buttonReleasedFunction, "+")


def bindButtonFunctionAndColor(target_widgets, enter_color, leave_color, clicked_color, buttonReleasedFunction):
    bindEnterAndLeaveColor(target_widgets, enter_color, leave_color)
    bindButtonPressColor(target_widgets, clicked_color, enter_color)
    bindButtonReleaseFunction(target_widgets, buttonReleasedFunction)

def unbindEnterLEaveButtonPressButtonReleaseFunction(target_widgets):
    for target_widget in target_widgets:
        for event_name in ["<Enter>", "<Leave>", "<ButtonPress>", "<ButtonRelease>"]:
            target_widget.unbind(event_name)

def unbindEventFromActiveTabWidget(active_tab_widget):
    for event_name in ["<Enter>", "<Leave>", "<ButtonPress>", "<ButtonRelease>"]:
        active_tab_widget.unbind(event_name)
        active_tab_widget.children["!ctklabel"].unbind(event_name)

def setDefaultActiveTab(active_tab_widget, active_bg_color, active_text_color):
    active_tab_widget.configure(fg_color=active_bg_color, cursor="")
    active_tab_widget.children["!ctklabel"].configure(fg_color=active_bg_color, text_color=active_text_color)
    unbindEventFromActiveTabWidget(active_tab_widget)


def switchActiveTabAndPassiveTab(active_tab_widget, current_active_tab_widget, current_active_tab_passive_function, hovered_color, clicked_color, passive_color):


    active_tab_widget.configure(cursor="")
    unbindEventFromActiveTabWidget(active_tab_widget)


    rebindFunctionToTab(current_active_tab_widget, current_active_tab_passive_function, hovered_color, clicked_color, passive_color)

def rebindFunctionToTab(passive_tab_widget, passive_tab_function, hovered_color, clicked_color,  passive_color):

    passive_tab_widget.configure(cursor="hand2")
    bindEnterAndLeaveColor([passive_tab_widget, passive_tab_widget.children["!ctklabel"]], hovered_color, passive_color)
    bindButtonPressColor([passive_tab_widget, passive_tab_widget.children["!ctklabel"]], clicked_color, passive_color)

    bindButtonReleaseFunction([passive_tab_widget, passive_tab_widget.children["!ctklabel"]], passive_tab_function)

def switchTabsColor(target_widget, tab_buttons, active_bg_color, active_text_color, passive_bg_color, passive_text_color):
    # Change all tabs' color to passive color at first
    for tab_button in tab_buttons:
        tab_button.configure(fg_color=passive_bg_color)
        tab_button.children["!ctklabel"].configure(fg_color=passive_bg_color, text_color=passive_text_color)

    # Then, set active color to the active tab
    target_widget.configure(fg_color=active_bg_color)
    target_widget.children["!ctklabel"].configure(fg_color=active_bg_color, text_color=active_text_color)






def createButtonWithImage(parent_widget, button_image_size, button_ipadxy, button_fg_color, button_enter_color=None, button_clicked_color=None, button_image_file=None, button_command=None, corner_radius:int=0, no_bind:bool=False):
    button_wrapper = CTkFrame(parent_widget, corner_radius=corner_radius, fg_color=button_fg_color, height=0, width=0)

    button_widget = CTkLabel(
        button_wrapper,
        text=None,
        height=0,
        image=CTkImage((button_image_file),size=(button_image_size,button_image_size)),
    )
    button_widget.grid(row=0, column=0, padx=button_ipadxy, pady=button_ipadxy)

    if no_bind is False:
        button_wrapper.configure(cursor="hand2")
        bindButtonFunctionAndColor(
            target_widgets=[button_wrapper, button_widget],
            enter_color=button_enter_color,
            leave_color=button_fg_color,
            clicked_color=button_clicked_color,
            buttonReleasedFunction=button_command,
        )

    return button_wrapper


def createLabelButton(parent_widget, label_button_bg_color, label_button_hovered_bg_color, label_button_clicked_bg_color, label_button_ipadx, label_button_ipady, variable, font_family, font_size, text_color, label_button_clicked_command, label_button_position=None, label_button_padx_between_img=0, label_button_min_height=None, label_button_min_width=None):

    label_button_box = CTkFrame(parent_widget, corner_radius=6, fg_color=label_button_bg_color, cursor="hand2")

    label_button_box.grid_rowconfigure(0, weight=1)
    if label_button_min_height is not None:
        label_button_box.grid_rowconfigure(0, minsize=label_button_min_height)

    label_button_box.grid_columnconfigure(0, weight=1)
    if label_button_min_width is not None:
        label_button_box.grid_columnconfigure(0, minsize=label_button_min_width)

    label_button_label_wrapper = CTkFrame(label_button_box, corner_radius=0, fg_color=label_button_bg_color)
    label_button_label_wrapper.grid(row=0, column=0, padx=label_button_ipadx, pady=label_button_ipady, sticky="ew")

    LABEL_COLUMN=0
    if label_button_position == "center":
        label_button_label_wrapper.grid_columnconfigure((0,2), weight=1)
        LABEL_COLUMN=1

    label_button_label_widget = CTkLabel(
        label_button_label_wrapper,
        textvariable=variable,
        height=0,
        font=CTkFont(family=font_family, size=font_size, weight="normal"),
        text_color=text_color
    )
    label_button_label_widget.grid(row=0, column=LABEL_COLUMN, padx=(0, label_button_padx_between_img))


    bindEnterAndLeaveColor([label_button_label_wrapper, label_button_box, label_button_label_widget], label_button_hovered_bg_color, label_button_bg_color)
    bindButtonPressColor([label_button_label_wrapper, label_button_box, label_button_label_widget], label_button_clicked_bg_color, label_button_hovered_bg_color)



    bindButtonReleaseFunction([label_button_label_wrapper, label_button_box, label_button_label_widget], label_button_clicked_command)

    def bindEventFromWidgets():
        bindButtonReleaseFunction([label_button_label_wrapper, label_button_box, label_button_label_widget], label_button_clicked_command)
    bindEventFromWidgets()

    def unbindEventFromWidgets():
        unbindEnterLEaveButtonPressButtonReleaseFunction([label_button_label_wrapper, label_button_box, label_button_label_widget])

    label_button_box.unbindFunction = unbindEventFromWidgets
    label_button_box.bindFunction = bindEventFromWidgets


    return (label_button_box, label_button_label_widget)





def createOptionMenuBox(parent_widget, optionmenu_bg_color, optionmenu_hovered_bg_color, optionmenu_clicked_bg_color, optionmenu_ipadx, optionmenu_ipady, variable, font_family, font_size, text_color, image_file, image_size, optionmenu_clicked_command, optionmenu_position=None, optionmenu_padx_between_img=0, optionmenu_min_height=None, optionmenu_min_width=None, setattr_widget=None, image_widget_attr_name=None):

    option_menu_box = CTkFrame(parent_widget, corner_radius=6, fg_color=optionmenu_bg_color, cursor="hand2")

    option_menu_box.grid_rowconfigure(0, weight=1)
    if optionmenu_min_height is not None:
        option_menu_box.grid_rowconfigure(0, minsize=optionmenu_min_height)

    option_menu_box.grid_columnconfigure(0, weight=1)
    if optionmenu_min_width is not None:
        option_menu_box.grid_columnconfigure(0, minsize=optionmenu_min_width)

    optionmenu_label_wrapper = CTkFrame(option_menu_box, corner_radius=0, fg_color=optionmenu_bg_color)
    optionmenu_label_wrapper.grid(row=0, column=0, padx=(optionmenu_ipadx[0],0), pady=optionmenu_ipady, sticky="ew")

    LABEL_COLUMN=0
    if optionmenu_position == "center":
        optionmenu_label_wrapper.grid_columnconfigure((0,2), weight=1)
        LABEL_COLUMN=1

    optionmenu_label_widget = CTkLabel(
        optionmenu_label_wrapper,
        textvariable=variable,
        height=0,
        font=CTkFont(family=font_family, size=font_size, weight="normal"),
        text_color=text_color
    )
    optionmenu_label_widget.grid(row=0, column=LABEL_COLUMN, padx=(0, optionmenu_padx_between_img))


    optionmenu_img_widget = CTkLabel(
        option_menu_box,
        text=None,
        corner_radius=0,
        height=0,
        image=CTkImage(image_file, size=image_size)
    )

    if image_widget_attr_name is not None:
        setattr(setattr_widget, image_widget_attr_name, optionmenu_img_widget)

    optionmenu_img_widget.grid(row=0, column=1, padx=(0, optionmenu_ipadx[1]), pady=optionmenu_ipady)


    bindEnterAndLeaveColor([optionmenu_label_wrapper, option_menu_box, optionmenu_label_widget, optionmenu_img_widget], optionmenu_hovered_bg_color, optionmenu_bg_color)
    bindButtonPressColor([optionmenu_label_wrapper, option_menu_box, optionmenu_label_widget, optionmenu_img_widget], optionmenu_clicked_bg_color, optionmenu_hovered_bg_color)


    def bindEventFromWidgets():
        bindButtonReleaseFunction([optionmenu_label_wrapper, option_menu_box, optionmenu_label_widget, optionmenu_img_widget], optionmenu_clicked_command)
    bindEventFromWidgets()

    def unbindEventFromWidgets():
        unbindEnterLEaveButtonPressButtonReleaseFunction([optionmenu_label_wrapper, option_menu_box, optionmenu_label_widget, optionmenu_img_widget])

    option_menu_box.unbindFunction = unbindEventFromWidgets
    option_menu_box.bindFunction = bindEventFromWidgets


    return (option_menu_box, optionmenu_label_widget, optionmenu_img_widget)


def applyUiScalingAndFixTheBugScrollBar(scrollbar_widget, padx, width):
    scrollbar_widget._scrollbar.grid_configure(padx=padx)

    # This is for CustomTkinter's spec change or bug fix.
    scrollbar_widget._scrollbar.configure(height=0)
    scrollbar_widget._scrollbar.configure(width=width)


def setGeometryToCenterOfScreen(root_widget):
    root_widget.update()
    sw=root_widget.winfo_screenwidth()
    sh=root_widget.winfo_screenheight()
    geometry_width = root_widget.winfo_width()
    geometry_height = root_widget.winfo_height()

    root_widget.geometry(str(geometry_width)+"x"+str(geometry_height)+"+"+str((sw-geometry_width)//2)+"+"+str((sh-geometry_height)//2))


def setGeometryToCenterOfTheWidget(attach_widget, target_widget):
    attach_widget.update()
    target_widget.update()
    current_window_x = attach_widget.winfo_rootx()
    current_window_y = attach_widget.winfo_rooty()
    current_window_width = attach_widget.winfo_width()
    current_window_height = attach_widget.winfo_height()
    desired_window_width = target_widget.winfo_width()
    desired_window_height = target_widget.winfo_height()

    desired_window_x = int((current_window_x + current_window_width / 2) - (desired_window_width / 2))
    desired_window_y = int((current_window_y + current_window_height / 2) - (desired_window_height / 2))

    target_widget.geometry(str(desired_window_width) + "x" + str(desired_window_height) + "+" + str(desired_window_x) + "+" + str(desired_window_y))


def fadeInAnimation(root_widget, steps:int=10, interval:float=0.1, max_alpha:float=1):
    alpha_steps = 100
    alpha_steps*=max_alpha
    step_size = alpha_steps/steps
    root_widget.attributes("-alpha", 0)
    num = 0
    while num < alpha_steps:
        if not root_widget.winfo_exists():
            break
        root_widget.attributes("-alpha", num / 100)
        root_widget.update()
        sleep(interval)
        num += step_size
    root_widget.attributes("-alpha", max_alpha)