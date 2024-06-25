
from os import path as os_path
import ctypes
from PIL import Image
import imgui
import imgui.integrations.opengl
import openvr
from OpenGL import GL

window_width = 1200
window_height = 800
FONT_SIZE_IN_PIXELS = 25

# Thanks: GPT4
def create_texture_fbo(width, height):
    # Generate framebuffer
    fbo = GL.glGenFramebuffers(1)
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, fbo)

    # Generate texture

    texture = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
    GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, width, height, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
    GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    # Attach texture to framebuffer
    GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, texture, 0)

    # Check for framebuffer completeness
    if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) != GL.GL_FRAMEBUFFER_COMPLETE:
        print("Framebuffer is not complete!")
        return None

    # Unbind framebuffer
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    return fbo, texture

def dispose_texture_fbo(fbo, texture):
    GL.glDeleteFramebuffers(1, [fbo])
    GL.glDeleteTextures(1, [texture])

class OpenVROverlayRenderer(imgui.integrations.opengl.ProgrammablePipelineRenderer):
    def __init__(self, overlay_handle, overlay_width, overlay_height, render_always = False):
        super().__init__()

        io = self.io

        io.display_size = overlay_width, overlay_height

        (fbo, texture) = create_texture_fbo(overlay_width, overlay_height)

        self.fbo = fbo
        self.texture = texture
        self.overlay_handle = overlay_handle
        self.render_always = render_always

        self.overlay = openvr.VROverlay()

        self.ovr_texture = openvr.Texture_t(
            handle=int(texture),
            eType=openvr.TextureType_OpenGL,
            eColorSpace=openvr.ColorSpace_Auto,
        )

        self.overlay.setOverlayMouseScale(overlay_handle, openvr.HmdVector2_t(overlay_width, overlay_height))

        self._gui_time = None

    def process_event(self, event_buffer):
        io = self.io

        if event_buffer.eventType == openvr.VREvent_MouseMove:
            io.mouse_pos = event_buffer.data.mouse.x, event_buffer.data.mouse.y
        elif event_buffer.eventType == openvr.VREvent_MouseButtonDown:
            if bool(event_buffer.data.mouse.button & openvr.VRMouseButton_Left):
                io.mouse_down[0] = True

        elif event_buffer.eventType == openvr.VREvent_MouseButtonUp:
            if bool(event_buffer.data.mouse.button & openvr.VRMouseButton_Left):
                io.mouse_down[0] = False

    def render(self, data):
        if not self.overlay.isActiveDashboardOverlay(self.overlay_handle) or not self.overlay.isDashboardVisible():
            if not self.render_always:
                return

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fbo)
        super().render(data)
        self.overlay.setOverlayTexture(self.overlay_handle, self.ovr_texture)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    def dispose(self):
        self.overlay.destroyOverlay(self.overlay_handle)
        dispose_texture_fbo(self.fbo, self.texture)

# Design
value_transparency = 100
value_theme = 0
value_ui_size = 0
value_text_box_font_size = 100
value_message_box_size = 1
value_font_family = 0
value_ui_language = 0
value_remember_the_main_window_position = True

def dashboardUI(font):
    global value_transparency
    global value_theme
    global value_ui_size
    global value_text_box_font_size
    global value_message_box_size
    global value_font_family
    global value_ui_language
    global value_remember_the_main_window_position

    imgui.new_frame()
    imgui.set_next_window_bg_alpha(1)
    imgui.set_next_window_position(0, 0)
    imgui.set_next_window_size(window_width, window_height)
    imgui.begin("Window", flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_SCROLLBAR)

    with imgui.font(font):
        with imgui.begin_tab_bar("MainTabBar"):
            with imgui.begin_tab_item("デザイン") as item:
                if item.selected:
                    with imgui.begin_table("DesignTable", 2):
                        imgui.table_next_row()
                        imgui.table_set_column_index(0)
                        imgui.text("Transparency")
                        imgui.table_set_column_index(1)
                        changed, value = imgui.slider_float(
                            "##Transparency",
                            value_transparency,
                            min_value=0,
                            max_value=100,
                        )
                        if changed:
                            value_transparency = value

                        imgui.table_next_row()
                        imgui.table_set_column_index(0)
                        imgui.text("Theme")
                        imgui.table_set_column_index(1)
                        list_theme = ["Light", "Dark", "System"]
                        clicked, value = imgui.combo(
                            "##Theme",
                            value_theme,
                            list_theme,
                        )
                        if clicked:
                            value_theme = value
                            print("Selected", list_theme[value_theme])

                        imgui.table_next_row()
                        imgui.table_set_column_index(0)
                        imgui.text("UI Size")
                        imgui.table_set_column_index(1)
                        list_ui_size = [f"{s}%" for s in range(40, 210, 10)]
                        clicked, value = imgui.combo(
                            "##UI Size",
                            value_ui_size,
                            list_ui_size,
                        )
                        if clicked:
                            value_ui_size = value
                            print("Selected", list_ui_size[value_ui_size])

                        imgui.table_next_row()
                        imgui.table_set_column_index(0)
                        imgui.text("Text Box Font Size")
                        imgui.table_set_column_index(1)
                        changed, value = imgui.slider_float(
                            "##Text Box Font Size",
                            value_text_box_font_size,
                            min_value=50,
                            max_value=200,
                        )
                        if changed:
                            value_text_box_font_size = value

                        imgui.table_next_row()
                        imgui.table_set_column_index(0)
                        imgui.text("Message Box Size")
                        imgui.table_set_column_index(1)
                        changed, value = imgui.slider_float(
                            "##Message Box Size",
                            value_message_box_size,
                            min_value=1,
                            max_value=99,
                        )
                        if changed:
                            value_message_box_size = value

                        imgui.table_next_row()
                        imgui.table_set_column_index(0)
                        imgui.text("Font Family")
                        imgui.table_set_column_index(1)
                        list_font_family = ["Arial", "YuGothic UI", "HG"]
                        clicked, value = imgui.combo(
                            "##Font Family",
                            value_font_family,
                            list_font_family,
                        )
                        if clicked:
                            value_font_family = value
                            print("Selected", list_font_family[value_font_family])

                        imgui.table_next_row()
                        imgui.table_set_column_index(0)
                        imgui.text("UI Language")
                        imgui.table_set_column_index(1)
                        list_ui_language = ["English", "Japanese"]
                        clicked, value = imgui.combo(
                            "##UI Language",
                            value_ui_language,
                            list_ui_language,
                        )
                        if clicked:
                            value_ui_language = value
                            print("Selected", list_ui_language[value_ui_language])

                        imgui.table_next_row()
                        imgui.table_set_column_index(0)
                        imgui.text("Remember The Main Window Position")
                        imgui.table_set_column_index(1)
                        clicked, flags = imgui.checkbox("##Remember The Main Window Position", value_remember_the_main_window_position)
                        if clicked:
                            value_remember_the_main_window_position = flags
                            print("Selected", value_remember_the_main_window_position)

            with imgui.begin_tab_item("Translate") as item:
                if item.selected:
                    pass

            with imgui.begin_tab_item("Transcription") as item:
                if item.selected:
                    pass

            with imgui.begin_tab_item("VR") as item:
                if item.selected:
                    pass

            with imgui.begin_tab_item("Other") as item:
                if item.selected:
                    pass

            with imgui.begin_tab_item("Advanced") as item:
                if item.selected:
                    pass
    imgui.end()

def fb_to_window_factor(window):
    import glfw
    win_w, win_h = glfw.get_window_size(window)
    fb_w, fb_h = glfw.get_framebuffer_size(window)

    return max(float(fb_w) / win_w, float(fb_h) / win_h)

def loadFonts(window):
    root  = os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))))
    font_scaling_factor = fb_to_window_factor(window)
    io = imgui.get_io()
    io.fonts.clear()
    io.font_global_scale = 1.0 / font_scaling_factor

    fonts = {
        "JP": io.fonts.add_font_from_file_ttf(
            os_path.join(root, "fonts", "NotoSansJP-Regular.ttf"),
            FONT_SIZE_IN_PIXELS * font_scaling_factor,
            glyph_ranges=io.fonts.get_glyph_ranges_japanese()
        ),
        "EN": io.fonts.add_font_from_file_ttf(
            os_path.join(root, "fonts", "NotoSansJP-Regular.ttf"),
            FONT_SIZE_IN_PIXELS * font_scaling_factor,
            glyph_ranges=io.fonts.get_glyph_ranges_default()
        ),
        "KR": io.fonts.add_font_from_file_ttf(
            os_path.join(root, "fonts", "NotoSansKR-Regular.ttf"),
            FONT_SIZE_IN_PIXELS * font_scaling_factor,
            glyph_ranges=io.fonts.get_glyph_ranges_korean()
        ),
        "SC": io.fonts.add_font_from_file_ttf(
            os_path.join(root, "fonts", "NotoSansSC-Regular.ttf"),
            FONT_SIZE_IN_PIXELS * font_scaling_factor,
            glyph_ranges=io.fonts.get_glyph_ranges_chinese_full()
        ),
        "TC": io.fonts.add_font_from_file_ttf(
            os_path.join(root, "fonts", "NotoSansTC-Regular.ttf"),
            FONT_SIZE_IN_PIXELS * font_scaling_factor,
            glyph_ranges=io.fonts.get_glyph_ranges_chinese_full()
        ),
    }
    return fonts

def main():
    import glfw
    import time

    # GLFW related init
    if not glfw.init():
        print("Failed to init glfw")
        return

    # we have to create some window for make GL work
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    window = glfw.create_window(16, 16, "", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)

    # OpenVR Init
    openvr.init(openvr.VRApplication_Background)
    overlay = openvr.VROverlay()

    dashboardKeyName = "VRCT.dashboard"
    dashboardFriendlyName = "VRCT Dashboard"
    (overlay_handle, overlay_icon_handle) = overlay.createDashboardOverlay(dashboardKeyName, dashboardFriendlyName)

    # init icon
    iconTexture = Image.open(os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "img", "vrct_logo_mark_black_icon.png"))
    iconWidth, iconHeight = iconTexture.size
    iconTexture = iconTexture.tobytes()
    iconTexture = (ctypes.c_char * len(iconTexture)).from_buffer_copy(iconTexture)
    overlay.setOverlayRaw(overlay_icon_handle, iconTexture, iconWidth, iconHeight, 4)

    # imgui init
    imgui.create_context()
    ui = OpenVROverlayRenderer(overlay_handle, window_width, window_height, render_always = True)

    # Load fonts
    fonts = loadFonts(window)

    ui.refresh_font_texture()

    # Buffer
    event_buffer = openvr.VREvent_t()

    try:
        while True:
            # OpenVR overlay event process
            while True:
                # second return value is event_buffer
                (has_event, _) = overlay.pollNextOverlayEvent(overlay_handle, event_buffer)

                if not has_event:
                    break

                ui.process_event(event_buffer)

                # Place UI here to make sure that we don't drop any events between sleep
                dashboardUI(fonts["JP"])
                imgui.core.end_frame()

            imgui.render()

            ui.render(imgui.get_draw_data())
            time.sleep(0.1)

    finally:
        ui.dispose()
        glfw.terminate()

def main_non_vr():
    import glfw
    import imgui.integrations.glfw

    # GLFW related init
    if not glfw.init():
        print("Failed to init glfw")
        return

    window = glfw.create_window(window_width, window_height, "", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)

    # imgui related init
    imgui.create_context()
    ui = imgui.integrations.glfw.GlfwRenderer(window)

    # Load Japanese font
    font_scaling_factor = fb_to_window_factor(window)
    io = imgui.get_io()
    io.fonts.clear()
    io.font_global_scale = 1.0 / font_scaling_factor

    # Load fonts
    fonts = loadFonts(window)

    ui.refresh_font_texture()

    # main loop
    try:
        while not glfw.window_should_close(window):
            # GLFW event update
            glfw.poll_events()

            # imgui related update
            ui.process_inputs()

            dashboardUI(fonts["JP"])

            imgui.render()
            ui.render(imgui.get_draw_data())

            # GLFW related update
            glfw.swap_buffers(window)

    finally:
        glfw.terminate()


if __name__ == "__main__":
    # main()
    main_non_vr()