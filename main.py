import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(0)

from vrct_gui.splash_window import SplashWindow
splash = SplashWindow()
splash.showSplash()

import controller

if __name__ == "__main__":
    controller.createMainWindow()
    splash.destroySplash()
    controller.showMainWindow()