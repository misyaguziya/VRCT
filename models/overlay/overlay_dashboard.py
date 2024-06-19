import os
import ctypes
import openvr
from PIL import Image

overlayKeyName = "VRCT.dashboard"
overlayFriendlyName = "VRCT Dashboard"
width = 1.5
alpha = 1.0
vecMouseScale = openvr.HmdVector2_t()

system = openvr.init(openvr.VRApplication_Background)
overlay = openvr.IVROverlay()
overlay_system = openvr.IVRSystem()
overlayHandle, thumbnailHandle = overlay.createDashboardOverlay(overlayKeyName, overlayFriendlyName)

overlay.setOverlayInputMethod(overlayHandle, openvr.VROverlayInputMethod_Mouse)
overlay.setOverlayWidthInMeters(overlayHandle, width)
overlay.setOverlayAlpha(overlayHandle, alpha)
overlay.setOverlayColor(overlayHandle, 1.0, 1.0, 1.0)

overlayTextureBounds = openvr.VRTextureBounds_t()
overlayTextureBounds.uMin = 1
overlayTextureBounds.vMin = 0
overlayTextureBounds.uMax = 1
overlayTextureBounds.vMax = 0
overlay.setOverlayTextureBounds(thumbnailHandle, overlayTextureBounds)
overlay.setOverlayTextureBounds(overlayHandle, overlayTextureBounds)

thumbnailTexture = Image.open("img/vrct_logo_mark_black_icon.png")
thumWidth, thumHeight = thumbnailTexture.size
thumbnailTexture = thumbnailTexture.tobytes()
thumbnailTexture = (ctypes.c_char * len(thumbnailTexture)).from_buffer_copy(thumbnailTexture)
overlay.setOverlayRaw(thumbnailHandle, thumbnailTexture, thumWidth, thumHeight, 4)

def update():
    event = openvr.VREvent_t()
    while overlay.pollNextOverlayEvent(overlayHandle, event):
        match event.eventType:
            case openvr.VREvent_MouseMove:
                mouseX = event.data.mouse.x
                mouseY = event.data.mouse.y
                print("Mouse move", mouseX, mouseY)
            case openvr.VREvent_MouseButtonDown:
                print("Mouse button down")
            case openvr.VREvent_MouseButtonUp:
                print("Mouse button up")
            case openvr.VREvent_DashboardActivated:
                print("Dashboard activated")
            case openvr.VREvent_DashboardDeactivated:
                print("Dashboard deactivated")
            case openvr.VREvent_DashboardRequested:
                print("Dashboard requested")
            case openvr.VREvent_EnterStandbyMode:
                print("Enter standby mode")
            case openvr.VREvent_LeaveStandbyMode:
                print("Leave standby mode")
            case openvr.VREvent_KeyboardCharInput:
                print("Keyboard char input")
            case openvr.VREvent_KeyboardClosed:
                print("Keyboard closed")
            case openvr.VREvent_KeyboardDone:
                print("Keyboard done")
            case openvr.VREvent_ResetDashboard:
                print("Reset dashboard")
            case openvr.VREvent_ScreenshotTriggered:
                print("Screenshot triggered")
            case openvr.VREvent_WirelessDisconnect:
                print("Wireless disconnect")
            case openvr.VREvent_WirelessReconnect:
                print("Wireless reconnect")
            case openvr.VREvent_Quit:
                print("Quit")
                openvr.shutdown()

    # if overlay.isDashboardVisible():
    #     try:
    #         thumbnailTexture = Image.open("img/vrct_logo_mark_black_icon.png")
    #         thumWidth, thumHeight = thumbnailTexture.size
    #         thumbnailTexture = thumbnailTexture.tobytes()
    #         thumbnailTexture = (ctypes.c_char * len(thumbnailTexture)).from_buffer_copy(thumbnailTexture)
    #         overlay.setOverlayRaw(thumbnailHandle, thumbnailTexture, thumWidth, thumHeight, 4)
    #     except Exception:
    #         pass

    if overlay.isOverlayVisible(overlayHandle) and overlay.isActiveDashboardOverlay(overlayHandle):
        overlayTexture = Image.open("img/about_vrct/vrct_logo_for_about_vrct.png")
        vecMouseScale.v0 = overlayTexture.size[0]
        vecMouseScale.v1 = overlayTexture.size[1]
        overlay.setOverlayMouseScale(overlayHandle, vecMouseScale)

        overlayWidth, overlayHeight = overlayTexture.size
        overlayTexture = overlayTexture.tobytes()
        overlayTexture = (ctypes.c_char * len(overlayTexture)).from_buffer_copy(overlayTexture)
        overlay.setOverlayRaw(overlayHandle, overlayTexture, overlayWidth, overlayHeight, 4)

import time

while True:
    update()
    time.sleep(0.1)