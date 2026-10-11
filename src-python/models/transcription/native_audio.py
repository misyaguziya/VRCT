"""Load the optional audio extension on first use, never at application import."""

import os
from functools import lru_cache
from importlib import import_module


@lru_cache(maxsize=1)
def get_native_audio():
    try:
        return import_module("vrct_audio")
    except ModuleNotFoundError as exc:
        if exc.name != "vrct_audio":
            raise
        # Source checkouts can run before the local wheel has been built.
        # A broken installed extension must surface instead of silently falling back.
        return None


def get_rust_devices():
    """VRCT_RUST_AUDIO=1: recording devices through vrct_audio (cpal / WASAPI, the Rust backend's)
    instead of PyAudioWPatch / pycaw, for checking it on real devices."""
    if os.environ.get("VRCT_RUST_AUDIO") != "1":
        return None
    native = get_native_audio()
    return native if native is not None and hasattr(native, "list_devices") else None


RUST_HOST_NAME = "Windows WASAPI"


def require_native_audio():
    """Recording and ordinary Google FLAC require the shipped native extension."""
    native = get_native_audio()
    if native is None:
        raise ImportError(
            "vrct_audio is required for audio recording and FLAC encoding. "
            "Build/install native/vrct-audio with the project's install script."
        )
    return native
