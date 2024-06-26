
from os import path as os_path
import ctypes
from PIL import Image
import imgui
import imgui.integrations.opengl
import openvr
from OpenGL import GL

window_width = 1000
window_height = 600
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

class BasePage():
    def __init__(self):
        pass

    def widgetTable(self, label, value):
        value_name = f"value_{label.replace(' ', '_').lower()}"
        imgui.table_next_row()
        imgui.table_set_column_index(0)
        imgui.text(label)
        imgui.table_set_column_index(1)
        available_width = imgui.get_content_region_available_width()
        imgui.push_item_width(available_width)
        if not hasattr(self, value_name):
            setattr(self, value_name, value)
        return value_name

    def widgetTextbox(self, label, value):
        value_name = self.widgetTable(label, value)
        changed, value = imgui.input_text(f"##{label}", value)
        if changed:
            setattr(self, value_name, value)
        return value_name

    def widgetCheckbox(self, label, value):
        value_name = self.widgetTable(label, value)
        clicked, flags = imgui.checkbox(f"##{label}", getattr(self, value_name))
        if clicked:
            setattr(self, value_name, flags)

    def widgetCombo(self, label, value, list):
        value_name = self.widgetTable(label, value)
        clicked, value = imgui.combo(
            f"##{label}",
            getattr(self, value_name),
            list,
        )
        if clicked:
            setattr(self, value_name, value)

    def widgetSlider(self, label, value, min_value, max_value):
        value_name = self.widgetTable(label, value)
        changed, value = imgui.slider_float(
            f"##{label}",
            getattr(self, value_name),
            min_value=min_value,
            max_value=max_value,
        )
        if changed:
            setattr(self, value_name, value)

class DesignPage(BasePage):
    def __init__(self):
        pass

    def show(self):
        with imgui.begin_table("DesignTable", 2):
            self.widgetSlider("Transparency", 100, 0, 100)
            self.widgetCombo("Theme", 0, ["Light", "Dark", "System"])
            self.widgetCombo("UI Size", 0, [f"{s}%" for s in range(40, 210, 10)])
            self.widgetSlider("Text Box Font Size", 100, 50, 200)
            self.widgetSlider("Message Box Size", 1, 1, 99)
            self.widgetCombo("Font Family", 0, ["Arial", "YuGothic UI", "HG"])
            self.widgetCombo("UI Language", 0, ["English", "Japanese"])
            self.widgetCheckbox("Remember The Main Window Position", True)

class TranslationPage(BasePage):
    def __init__(self):
        pass

    def show(self):
        with imgui.begin_table("DesignTable", 2):
            self.widgetCheckbox("Use Translation Feature", True)
            self.widgetCombo("Select Internal Translation Model", 0, ["Basic model (418MB)", "High accuracy model (1.2GB)"])
            self.widgetTextbox("DeepL Auth Key", "")

class TranscriptionPage(BasePage):
    def __init__(self):
        pass

    def show(self):
        imgui.text("Mic")
        with imgui.begin_table("TranscriptionTableMic", 2):
            self.widgetCombo("Mic Host/Driver", 0, ["MME", "Windows DirectSound", "Windows WASAPI"])
            self.widgetCombo("Mic Device", 0, ["1", "2", "3"])
            self.widgetCheckbox("Mic Energy Threshold (Automatic)", True)
            self.widgetSlider("Mic Energy Threshold", 300, 0, 2000)
            self.widgetTextbox("Mic Record Timeout", "3")
            self.widgetTextbox("Mic Phrase Timeout", "3")
            self.widgetTextbox("Mic Max Words", "10")

        imgui.separator()
        imgui.text("Speaker")
        with imgui.begin_table("TranscriptionTableSpeaker", 2):
            self.widgetCombo("Speaker Device", 0, ["1", "2", "3"])
            self.widgetCheckbox("Speaker Energy Threshold (Automatic)", True)
            self.widgetSlider("Speaker Energy Threshold", 300, 0, 4000)
            self.widgetTextbox("Speaker Record Timeout", "3")
            self.widgetTextbox("Speaker Phrase Timeout", "3")
            self.widgetTextbox("Speaker Max Words", "10")

        imgui.separator()
        imgui.text("Transcription Model")
        with imgui.begin_table("TranscriptionTableModel", 2):
            self.widgetCheckbox("Use Whisper Model As Transcription", False)
            self.widgetCombo("Select Whisper Model", 0, ["tiny", "base", "small", "medium", "large"])

class VRPage(BasePage):
    def __init__(self):
        pass

    def show(self):
        with imgui.begin_table("VRTable", 2):
            self.widgetCheckbox("Enable Overlay", True)
            self.widgetCheckbox("Notification XSOverlay", False)

class OtherPage(BasePage):
    def __init__(self):
        pass

    def show(self):
        with imgui.begin_table("OtherTable", 2):
            self.widgetCheckbox("Auto Clear The Message Box", True)
            self.widgetCheckbox("Send Only Translated Messages", False)
            self.widgetCombo("Send Message Button", 0, ["Hide (Use enter key to send)", "Show", "Show and disable to send when pressed enter key"])
            self.widgetCheckbox("Auto Export Message Logs", False)
            self.widgetCheckbox("VRC Mic Mute Sync", False)
            self.widgetCheckbox("Send Message To VRChat", False)

class AdvancedPage(BasePage):
    def __init__(self):
        pass

    def show(self):
        with imgui.begin_table("AdvancedTable", 2):
            self.widgetTextbox("OSC IP Address", "127.0.0.1")
            self.widgetTextbox("OSC Port", "9000")

design_page = DesignPage()
translation_page = TranslationPage()
transcription_page = TranscriptionPage()
vr_page = VRPage()
other_page = OtherPage()
advanced_page = AdvancedPage()

def dashboardUI(font):
    imgui.new_frame()
    imgui.set_next_window_bg_alpha(1)
    imgui.set_next_window_position(0, 0)
    imgui.set_next_window_size(window_width, window_height)
    imgui.begin("Window", flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_SCROLLBAR)

    with imgui.font(font):
        with imgui.begin_tab_bar("MainTabBar"):
            # with imgui.begin_tab_item("Design") as item:
            #     if item.selected:
            #         design_page.show()

            with imgui.begin_tab_item("Translation") as item:
                if item.selected:
                    translation_page.show()

            with imgui.begin_tab_item("Transcription") as item:
                if item.selected:
                    transcription_page.show()

            with imgui.begin_tab_item("VR") as item:
                if item.selected:
                    vr_page.show()

            with imgui.begin_tab_item("Other") as item:
                if item.selected:
                    other_page.show()

            with imgui.begin_tab_item("Advanced") as item:
                if item.selected:
                    advanced_page.show()
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
    window = glfw.create_window(window_width, window_height, "", None, None)
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

    # init dashboard
    overlay.setOverlayWidthInMeters(overlay_handle, 2.5)

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