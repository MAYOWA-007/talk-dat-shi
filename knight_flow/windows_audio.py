from __future__ import annotations

import ctypes
import logging
import sys
import threading
import uuid
from ctypes import wintypes


log = logging.getLogger(__name__)

_WINFUNCTYPE = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
_HRESULT = ctypes.c_long
_CLSCTX_ALL = 0x17
_COINIT_APARTMENTTHREADED = 0x2
_RPC_E_CHANGED_MODE = 0x80010106
_E_RENDER = 0
_E_CONSOLE = 0


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(value: str) -> GUID:
    item = uuid.UUID(value)
    return GUID(
        item.time_low,
        item.time_mid,
        item.time_hi_version,
        (ctypes.c_ubyte * 8)(*item.bytes[8:]),
    )


_CLSID_MM_DEVICE_ENUMERATOR = _guid("BCDE0395-E52F-467C-8E3D-C4579291692E")
_IID_IMM_DEVICE_ENUMERATOR = _guid("A95664D2-9614-4F35-A746-DE8DB63617E6")
_IID_IAUDIO_ENDPOINT_VOLUME = _guid("5CDF2C82-841E-4546-9722-0CF74078229A")


def _failed(hr: int) -> bool:
    return ctypes.c_int32(int(hr)).value < 0


def _hr_text(hr: int) -> str:
    return f"0x{ctypes.c_uint32(int(hr)).value:08X}"


def _check(hr: int, label: str) -> None:
    if _failed(hr):
        raise OSError(f"{label} failed with HRESULT {_hr_text(hr)}")


def _method(ptr: ctypes.c_void_p, index: int, restype: object, *argtypes: object) -> object:
    vtable = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    prototype = _WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return prototype(vtable[index])


def _release(ptr: ctypes.c_void_p | None) -> None:
    if not ptr or not ptr.value:
        return
    try:
        release = _method(ptr, 2, ctypes.c_ulong)
        release(ptr)
    except Exception:
        pass


def _co_initialize() -> bool:
    ole32 = ctypes.windll.ole32
    hr = ole32.CoInitializeEx(None, _COINIT_APARTMENTTHREADED)
    code = ctypes.c_uint32(int(hr)).value
    if code == _RPC_E_CHANGED_MODE:
        return False
    _check(hr, "CoInitializeEx")
    return True


def _default_endpoint_volume() -> tuple[ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]:
    ole32 = ctypes.windll.ole32
    enumerator = ctypes.c_void_p()
    device = ctypes.c_void_p()
    volume = ctypes.c_void_p()

    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(GUID),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(GUID),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    ole32.CoCreateInstance.restype = _HRESULT
    hr = ole32.CoCreateInstance(
        ctypes.byref(_CLSID_MM_DEVICE_ENUMERATOR),
        None,
        _CLSCTX_ALL,
        ctypes.byref(_IID_IMM_DEVICE_ENUMERATOR),
        ctypes.byref(enumerator),
    )
    _check(hr, "CoCreateInstance(IMMDeviceEnumerator)")

    get_default_audio_endpoint = _method(
        enumerator,
        4,
        _HRESULT,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
    )
    hr = get_default_audio_endpoint(enumerator, _E_RENDER, _E_CONSOLE, ctypes.byref(device))
    _check(hr, "GetDefaultAudioEndpoint")

    activate = _method(
        device,
        3,
        _HRESULT,
        ctypes.POINTER(GUID),
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    )
    hr = activate(device, ctypes.byref(_IID_IAUDIO_ENDPOINT_VOLUME), _CLSCTX_ALL, None, ctypes.byref(volume))
    _check(hr, "Activate(IAudioEndpointVolume)")
    return enumerator, device, volume


def get_default_output_muted() -> bool:
    if sys.platform != "win32":
        return False
    initialized = _co_initialize()
    enumerator: ctypes.c_void_p | None = None
    device: ctypes.c_void_p | None = None
    volume: ctypes.c_void_p | None = None
    try:
        enumerator, device, volume = _default_endpoint_volume()
        muted = wintypes.BOOL()
        get_mute = _method(volume, 15, _HRESULT, ctypes.POINTER(wintypes.BOOL))
        hr = get_mute(volume, ctypes.byref(muted))
        _check(hr, "GetMute")
        return bool(muted.value)
    finally:
        _release(volume)
        _release(device)
        _release(enumerator)
        if initialized:
            ctypes.windll.ole32.CoUninitialize()


def set_default_output_muted(muted: bool) -> None:
    if sys.platform != "win32":
        return
    initialized = _co_initialize()
    enumerator: ctypes.c_void_p | None = None
    device: ctypes.c_void_p | None = None
    volume: ctypes.c_void_p | None = None
    try:
        enumerator, device, volume = _default_endpoint_volume()
        set_mute = _method(volume, 14, _HRESULT, wintypes.BOOL, ctypes.c_void_p)
        hr = set_mute(volume, wintypes.BOOL(1 if muted else 0), None)
        _check(hr, "SetMute")
    finally:
        _release(volume)
        _release(device)
        _release(enumerator)
        if initialized:
            ctypes.windll.ole32.CoUninitialize()


class OutputMuteGuard:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active = False
        self._previous_mute: bool | None = None

    def start(self, *, enabled: bool = True) -> None:
        if not enabled:
            return
        with self._lock:
            if self._active:
                return
            try:
                self._previous_mute = get_default_output_muted()
                set_default_output_muted(True)
                self._active = True
                log.info("default output audio muted for dictation")
            except Exception as exc:
                self._previous_mute = None
                self._active = False
                log.warning("could not mute default output audio: %s", exc)

    def stop(self) -> None:
        with self._lock:
            if not self._active:
                return
            previous = self._previous_mute
            self._active = False
            self._previous_mute = None
        if previous is None:
            return
        try:
            set_default_output_muted(previous)
            log.info("default output audio mute restored")
        except Exception as exc:
            log.warning("could not restore default output audio mute: %s", exc)
