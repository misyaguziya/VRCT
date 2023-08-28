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