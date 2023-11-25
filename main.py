if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(0)

        from vrct_gui.splash_window import SplashWindow
        splash = SplashWindow()
        splash.showSplash()

        from config import config
        from models.translation.utils import downloadCTranslate2Weight
        downloadCTranslate2Weight(config.PATH_LOCAL, config.WEIGHT_TYPE, config.CTRANSLATE2_WIGHTS)

        import controller
        controller.createMainWindow()
        splash.destroySplash()
        controller.showMainWindow()

    except Exception:
        import traceback
        with open('error.log', 'a') as f:
            traceback.print_exc(file=f)