"""Windows D3D11 mirror texture reader for the OpenVR compositor.

Used by OCR (ocr_capture_openvr.py) and by the standalone tools under tools/,
which load this file by path. Keep it free of VRCT imports so that works.

No OpenVR session is initialized here. Callers own init/shutdown and must
create, read and close these resources on the same thread. Acquire the mirror
once and reuse it every frame; releasing and re-acquiring per frame makes
SteamVR serve stale frames (ValveSoftware/openvr#1888).
"""

from __future__ import annotations

import ctypes as ct
import uuid


def _validate_pixel_layout(width, height, row_pitch, view_format, color_order):
    if color_order not in ("RGB", "BGR"):
        raise ValueError("color_order must be RGB or BGR")
    if view_format not in (28, 29, 87, 91):
        raise ValueError("unsupported typed DXGI pixel format")
    if (type(width) is not int or type(height) is not int or type(row_pitch) is not int
            or width <= 0 or height <= 0 or row_pitch < width * 4):
        raise ValueError("invalid mapped pixel dimensions or row pitch")


def _pixels_from_bytes(raw, width, height, row_pitch, view_format, color_order="RGB"):
    """Return owned, writable contiguous pixels; retain D3D's top-row ordering."""
    import numpy as np

    _validate_pixel_layout(width, height, row_pitch, view_format, color_order)
    if not isinstance(raw, bytes):
        raise TypeError("mapped pixels must be an owned bytes copy")
    required = row_pitch * height
    if len(raw) < required:
        raise ValueError("mapped pixel buffer is shorter than its layout")
    rows = np.frombuffer(raw, dtype=np.uint8, count=required).reshape(height, row_pitch)
    pixels = rows[:, :width * 4].reshape(height, width, 4)
    try:
        import cv2
    except ModuleNotFoundError as error:
        if error.name != "cv2":
            raise
        input_is_bgr = view_format in (87, 91)
        channels = pixels[:, :, :3]
        if input_is_bgr != (color_order == "BGR"):
            channels = channels[:, :, ::-1]
        # ascontiguousarray alone can alias readonly input for singleton images.
        return np.array(channels, dtype=np.uint8, copy=True, order="C")
    conversion = {
        (False, "RGB"): cv2.COLOR_RGBA2RGB,
        (False, "BGR"): cv2.COLOR_RGBA2BGR,
        (True, "RGB"): cv2.COLOR_BGRA2RGB,
        (True, "BGR"): cv2.COLOR_BGRA2BGR,
    }[(view_format in (87, 91), color_order)]
    return cv2.cvtColor(pixels, conversion)


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

    def read(self, *, color_order="RGB"):
        if color_order not in ("RGB", "BGR"):
            raise ValueError("color_order must be RGB or BGR")
        com_call(self.context, 47, None, [ct.c_void_p, ct.c_void_p],
                 self.staging, self.texture)
        mapped = MappedResource()
        check_hr(com_call(self.context, 14, ct.c_long,
                          [ct.c_void_p, ct.c_uint, ct.c_uint, ct.c_uint,
                           ct.POINTER(MappedResource)],
                          self.staging, 0, 1, 0, ct.byref(mapped)), "Map")
        try:
            self.row_pitch = mapped.RowPitch
            _validate_pixel_layout(self.desc.Width, self.desc.Height, mapped.RowPitch,
                                   self.view_format, color_order)
            if not mapped.pData:
                raise ValueError("Map returned a null pixel pointer")
            raw = ct.string_at(mapped.pData, mapped.RowPitch * self.desc.Height)
            return _pixels_from_bytes(raw, self.desc.Width, self.desc.Height,
                                      mapped.RowPitch, self.view_format, color_order)
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
