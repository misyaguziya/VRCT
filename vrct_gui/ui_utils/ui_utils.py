from os import path as os_path
from PIL.Image import open as Image_open, LANCZOS

from customtkinter import CTkFrame, CTkLabel, CTkImage

def getImagePath(file_name):
    # root\img\file_name
    return os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "img", file_name)

def getImageFileFromUiUtils(file_name):
    # root\img\file_name
    img = Image_open(os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "img", file_name))
    return img

def openImageKeepAspectRatio(file_name, desired_width):
    img = getImageFileFromUiUtils(file_name)
    wpercent = (desired_width/float(img.size[0]))
    hsize = int((float(img.size[1])*float(wpercent)))
    img = img.resize((desired_width,hsize), LANCZOS)
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

def getLongestText(settings):
    max_length = max(len(item["text"]) for item in settings)
    max_length = 0
    longest_text = ""

    for item in settings:
        if len(item["text"]) > max_length:
            max_length = len(item["text"])
            longest_text = item["text"]
    return longest_text

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






def createButtonWithImage(parent_widget, button_fg_color, button_enter_color, button_clicked_color, button_image_filename, button_image_size, button_ipadxy, button_command, corner_radius: int = 0 ,shape: str = "normal"):
        button_wrapper = CTkFrame(parent_widget, corner_radius=corner_radius, fg_color=button_fg_color, height=0, width=0, cursor="hand2")

        button_widget = CTkLabel(
            button_wrapper,
            text=None,
            height=0,
            image=CTkImage(getImageFileFromUiUtils(button_image_filename),size=(button_image_size,button_image_size)),
        )
        button_widget.grid(row=0, column=0, padx=button_ipadxy, pady=button_ipadxy)

        bindButtonFunctionAndColor(
            target_widgets=[button_wrapper, button_widget],
            enter_color=button_enter_color,
            leave_color=button_fg_color,
            clicked_color=button_clicked_color,
            buttonReleasedFunction=button_command,
        )

        if shape == "circle":
            # To round the corners of the button into a circle
            button_wrapper.grid()
            button_wrapper.configure(corner_radius=int(getLatestWidth(button_wrapper)/2))
            button_wrapper.grid_remove()


        return button_wrapper
