import ctypes
import openvr
from PIL import Image

overlayKeyName = "VRCT.dashboard"
overlayFriendlyName = "VRCT Dashboard"
width = 1.0
alpha = 1.0
vecMouseScale = openvr.HmdVector2_t()

system = openvr.init(openvr.VRApplication_Overlay)
overlay = openvr.IVROverlay()
overlay_system = openvr.IVRSystem()
dashboardHandle, thumbnailHandle = overlay.createDashboardOverlay(overlayKeyName, overlayFriendlyName)

overlay.setOverlayInputMethod(dashboardHandle, openvr.VROverlayInputMethod_Mouse)
overlay.setOverlayWidthInMeters(dashboardHandle, width)
overlay.setOverlayAlpha(dashboardHandle, alpha)
overlay.setOverlayColor(dashboardHandle, 1.0, 1.0, 1.0)

thumbnailTexture = Image.open("logo.png")
thumWidth, thumHeight = thumbnailTexture.size
thumbnailTexture = thumbnailTexture.tobytes()
thumbnailTexture = (ctypes.c_char * len(thumbnailTexture)).from_buffer_copy(thumbnailTexture)
overlay.setOverlayRaw(thumbnailHandle, thumbnailTexture, thumWidth, thumHeight, 4)


def update():
    event = openvr.VREvent_t()
    while overlay.pollNextOverlayEvent(dashboardHandle, event):
        match event.eventType:
            case openvr.VREvent_MouseMove:
                mouseX = event.data.mouse.x
                mouseY = event.data.mouse.y
                print("Mouse move", mouseX, mouseY)
                break
            case openvr.VREvent_MouseButtonDown:
                print("Mouse button down")
                break
            case openvr.VREvent_MouseButtonUp:
                print("Mouse button up")
                break
            case openvr.VREvent_DashboardActivated:
                print("Dashboard activated")
                break
            case openvr.VREvent_DashboardDeactivated:
                print("Dashboard deactivated")
                break
            case openvr.VREvent_DashboardRequested:
                print("Dashboard requested")
                break
            case openvr.VREvent_EnterStandbyMode:
                print("Enter standby mode")
                break
            case openvr.VREvent_LeaveStandbyMode:
                print("Leave standby mode")
                break
            case openvr.VREvent_KeyboardCharInput:
                print("Keyboard char input")
                break
            case openvr.VREvent_KeyboardClosed:
                print("Keyboard closed")
                break
            case openvr.VREvent_KeyboardDone:
                print("Keyboard done")
                break
            case openvr.VREvent_ResetDashboard:
                print("Reset dashboard")
                break
            case openvr.VREvent_ScreenshotTriggered:
                print("Screenshot triggered")
                break
            case openvr.VREvent_WirelessDisconnect:
                print("Wireless disconnect")
                break
            case openvr.VREvent_WirelessReconnect:
                print("Wireless reconnect")
                break
            case openvr.VREvent_Quit:
                print("Quit")
                openvr.shutdown()

    if overlay.isOverlayVisible(dashboardHandle) and overlay.isActiveDashboardOverlay(dashboardHandle):
        dashboardTexture = Image.new("RGBA", (1024, 768), (255, 255, 255, 255))
        dashboardWidth, dashboardHeight = dashboardTexture.size

        dashboardTexture = dashboardTexture.tobytes()
        dashboardTexture = (ctypes.c_char * len(dashboardTexture)).from_buffer_copy(dashboardTexture)
        overlay.setOverlayRaw(dashboardHandle, dashboardTexture, dashboardWidth, dashboardHeight, 4)

import time

while True:
    update()
    time.sleep(0.1)