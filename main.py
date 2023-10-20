if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(0)

        from vrct_gui.splash_window import SplashWindow
        splash = SplashWindow()
        splash.showSplash()

        import controller
        controller.createMainWindow()
        splash.destroySplash()
        controller.showMainWindow()

    except Exception as e:
        import traceback
        with open('error.log', 'a') as f:
            traceback.print_exc(file=f)