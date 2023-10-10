from os import path as os_path
from PIL.Image import open as Image_open

def getImageFile(file_name):
    img = Image_open(os_path.join(os_path.dirname(__file__), "img", file_name))
    return img

def get_key_by_value(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None

def callFunctionIfCallable(function, *args):
    if callable(function) is True: function(*args)

def isEven(number):
    return number % 2 == 0

def makeEven(number):
    return number if isEven(number) else number + 1