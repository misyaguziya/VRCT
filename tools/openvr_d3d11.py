"""Windows D3D11 mirror primitives shared by standalone capture tools.

No OpenVR session is initialized at import. Callers own init/shutdown and must
create, read and close these resources on the same thread.
"""

from __future__ import annotations

import ctypes as ct
from ctypes import wintypes as wt
import uuid


class TextureDesc(ct.Structure):
    """D3D11_TEXTURE2D_DESC (including its inline DXGI_SAMPLE_DESC)."""

    _fields_ = [(name, ct.c_uint32) for name in (
        "Width", "Height", "MipLevels", "ArraySize", "Format", "SampleCount",
        "SampleQuality", "Usage", "BindFlags", "CPUAccessFlags", "MiscFlags",
    )]


class MappedResource(ct.Structure):
    _fields_ = [("pData", ct.c_void_p), ("RowPitch", ct.c_uint32),
                ("DepthPitch", ct.c_uint32)]


def com_call(obj, slot, result, argtypes, *args):
    """Call a Windows COM method. Slots follow the Windows SDK headers."""
    vtable = ct.cast(obj, ct.POINTER(ct.POINTER(ct.c_void_p))).contents
    return ct.WINFUNCTYPE(result, ct.c_void_p, *argtypes)(vtable[slot])(obj, *args)


def release(obj):
    if obj:
        com_call(obj, 2, ct.c_ulong, [])


def check_hr(value, operation):
    if value < 0:
        raise RuntimeError(f"{operation}: HRESULT 0x{value & 0xffffffff:08x}")


class D3D11Mirror:
    """Acquire once, copy to CPU staging repeatedly, release on exit."""

    def __init__(self, system, compositor, eye):
        self.compositor = compositor
        self.device = ct.c_void_p()
        self.context = ct.c_void_p()
        self.srv = ct.c_void_p()
        self.texture = ct.c_void_p()
        self.staging = ct.c_void_p()
        self.desc = TextureDesc()
        self.adapter_index = system.getDXGIOutputInfo()
        self.row_pitch = None
        factory, adapter = ct.c_void_p(), ct.c_void_p()
        try:
            dxgi = ct.WinDLL("dxgi")
            iid = (ct.c_ubyte * 16).from_buffer_copy(
                uuid.UUID("7b7166ec-21c7-44ae-b21a-c9ae321ae369").bytes_le)
            dxgi.CreateDXGIFactory.argtypes = [ct.c_void_p, ct.POINTER(ct.c_void_p)]
            dxgi.CreateDXGIFactory.restype = ct.c_long
            check_hr(dxgi.CreateDXGIFactory(ct.byref(iid), ct.byref(factory)),
                     "CreateDXGIFactory")
            if self.adapter_index < 0:
                raise RuntimeError("SteamVR did not return a DXGI adapter")
            check_hr(com_call(factory, 7, ct.c_long,
                              [ct.c_uint, ct.POINTER(ct.c_void_p)],
                              self.adapter_index, ct.byref(adapter)), "EnumAdapters")
            d3d = ct.WinDLL("d3d11")
            create = d3d.D3D11CreateDevice
            create.argtypes = [ct.c_void_p, ct.c_uint, ct.c_void_p, ct.c_uint,
                               ct.c_void_p, ct.c_uint, ct.c_uint,
                               ct.POINTER(ct.c_void_p), ct.POINTER(ct.c_uint),
                               ct.POINTER(ct.c_void_p)]
            create.restype = ct.c_long
            level = ct.c_uint()
            check_hr(create(adapter, 0, None, 0, None, 0, 7,
                            ct.byref(self.device), ct.byref(level),
                            ct.byref(self.context)), "D3D11CreateDevice")
            # pyopenvr 1.26.701's convenience wrapper incorrectly adds byref
            # to the input void*. Its typed function table has the correct ABI.
            error = compositor.function_table.getMirrorTextureD3D11(
                eye, self.device, ct.byref(self.srv))
            if error:
                raise RuntimeError(f"GetMirrorTextureD3D11: OpenVR error {error}")
            if not self.srv:
                raise RuntimeError("GetMirrorTextureD3D11 returned null")
            com_call(self.srv, 7, None, [ct.POINTER(ct.c_void_p)],
                     ct.byref(self.texture))  # ID3D11View::GetResource adds a ref
            com_call(self.texture, 10, None, [ct.POINTER(TextureDesc)],
                     ct.byref(self.desc))
            # The compositor can expose a TYPELESS resource with a typed SRV.
            # D3D11_SHADER_RESOURCE_VIEW_DESC begins with Format/ViewDimension.
            view_desc = (ct.c_uint32 * 16)()
            com_call(self.srv, 8, None, [ct.c_void_p], ct.byref(view_desc))
            self.view_format = int(view_desc[0])
            if (self.desc.Format not in (27, 28, 29, 87, 90, 91)
                    or self.view_format not in (28, 29, 87, 91)):
                raise RuntimeError(f"Unsupported DXGI format: {self.desc.Format}")
            if (self.desc.SampleCount != 1 or self.desc.ArraySize != 1
                    or self.desc.MipLevels != 1):
                raise RuntimeError("Probe expects a single-sample, single-mip 2D texture")
            staging_desc = TextureDesc.from_buffer_copy(self.desc)
            staging_desc.Format = self.view_format
            staging_desc.Usage = 3  # D3D11_USAGE_STAGING
            staging_desc.BindFlags = 0
            staging_desc.CPUAccessFlags = 0x20000  # D3D11_CPU_ACCESS_READ
            staging_desc.MiscFlags = 0
            check_hr(com_call(self.device, 5, ct.c_long,
                              [ct.POINTER(TextureDesc), ct.c_void_p,
                               ct.POINTER(ct.c_void_p)],
                              ct.byref(staging_desc), None, ct.byref(self.staging)),
                     "CreateTexture2D")
        except BaseException:
            self.close()
            raise
        finally:
            release(adapter)
            release(factory)

    def read(self):
        import numpy as np

        com_call(self.context, 47, None, [ct.c_void_p, ct.c_void_p],
                 self.staging, self.texture)
        mapped = MappedResource()
        check_hr(com_call(self.context, 14, ct.c_long,
                          [ct.c_void_p, ct.c_uint, ct.c_uint, ct.c_uint,
                           ct.POINTER(MappedResource)],
                          self.staging, 0, 1, 0, ct.byref(mapped)), "Map")
        try:
            self.row_pitch = mapped.RowPitch
            raw = ct.string_at(mapped.pData, mapped.RowPitch * self.desc.Height)
            rows = np.frombuffer(raw, dtype=np.uint8).reshape(
                self.desc.Height, mapped.RowPitch)
            rgba = rows[:, :self.desc.Width * 4].reshape(
                self.desc.Height, self.desc.Width, 4)
            rgb = rgba[:, :, [2, 1, 0]] if self.view_format in (87, 91) else rgba[:, :, :3]
            # D3D top row is row zero. Do not apply the GL path's vertical flip.
            return np.ascontiguousarray(rgb)
        finally:
            com_call(self.context, 15, None, [ct.c_void_p, ct.c_uint], self.staging, 0)

    def close(self):
        release(self.staging)
        self.staging = ct.c_void_p()
        release(self.texture)
        self.texture = ct.c_void_p()
        if self.srv:
            self.compositor.function_table.releaseMirrorTextureD3D11(self.srv)
            self.srv = ct.c_void_p()
        release(self.context)
        self.context = ct.c_void_p()
        release(self.device)
        self.device = ct.c_void_p()


def vrchat_windows():
    """Read window state only; do not focus, restore or minimize anything."""
    import psutil

    pids = {p.info["pid"] for p in psutil.process_iter(["pid", "name"])
            if (p.info["name"] or "").lower() == "vrchat.exe"}
    user32 = ct.WinDLL("user32", use_last_error=True)
    callback_type = ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wt.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ct.POINTER(wt.DWORD)]
    user32.IsIconic.argtypes = [wt.HWND]
    user32.IsWindowVisible.argtypes = [wt.HWND]
    user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ct.c_int]
    windows = []

    @callback_type
    def visit(hwnd, _):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ct.byref(pid))
        if pid.value in pids:
            title = ct.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)
            if title.value == "VRChat":
                windows.append({"pid": pid.value, "hwnd": int(hwnd),
                                "minimized": bool(user32.IsIconic(hwnd)),
                                "visible": bool(user32.IsWindowVisible(hwnd))})
        return True

    user32.EnumWindows(visit, 0)
    return windows
