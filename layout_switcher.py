"""
Layout switching via TIS (Text Input Source) API using pure ctypes.
"""

import ctypes
import ctypes.util
import threading

_carbon = None
_prop_key_layout_data = None   # cached CFString for TISPropertyUnicodeKeyLayoutData
_prop_key_source_id = None     # cached CFString for TISPropertyInputSourceID

_LANG_TO_IDS: dict[str, list[bytes]] = {
    'ru': [b'com.apple.keylayout.Russian', b'com.apple.keylayout.Russian-PC', b'com.apple.keylayout.RussianWin'],
    'uk': [b'com.apple.keylayout.Ukrainian', b'com.apple.keylayout.Ukrainian-PC'],
    'en': [b'com.apple.keylayout.ABC', b'com.apple.keylayout.US'],
}

_kCFStringEncodingUTF8 = 0x08000100


def _get_carbon() -> ctypes.CDLL | None:
    global _carbon
    if _carbon is not None:
        return _carbon
    path = ctypes.util.find_library('Carbon')
    if not path:
        return None
    lib = ctypes.cdll.LoadLibrary(path)

    lib.TISCreateInputSourceList.restype = ctypes.c_void_p
    lib.TISCreateInputSourceList.argtypes = [ctypes.c_void_p, ctypes.c_bool]

    lib.CFArrayGetCount.restype = ctypes.c_long
    lib.CFArrayGetCount.argtypes = [ctypes.c_void_p]

    lib.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
    lib.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]

    lib.TISGetInputSourceProperty.restype = ctypes.c_void_p
    lib.TISGetInputSourceProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    lib.TISSelectInputSource.restype = ctypes.c_int
    lib.TISSelectInputSource.argtypes = [ctypes.c_void_p]

    lib.CFStringCreateWithCString.restype = ctypes.c_void_p
    lib.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]

    lib.CFStringGetCString.restype = ctypes.c_bool
    lib.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]

    lib.CFRelease.restype = None
    lib.CFRelease.argtypes = [ctypes.c_void_p]

    lib.TISCopyCurrentKeyboardInputSource.restype = ctypes.c_void_p
    lib.TISCopyCurrentKeyboardInputSource.argtypes = []

    lib.CFDataGetBytePtr.restype = ctypes.c_void_p
    lib.CFDataGetBytePtr.argtypes = [ctypes.c_void_p]

    lib.UCKeyTranslate.restype = ctypes.c_int
    lib.UCKeyTranslate.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint16,
        ctypes.c_uint16,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_long,
        ctypes.POINTER(ctypes.c_long),
        ctypes.c_wchar_p,
    ]

    _carbon = lib

    global _prop_key_layout_data, _prop_key_source_id
    _prop_key_layout_data = lib.CFStringCreateWithCString(
        None, b'TISPropertyUnicodeKeyLayoutData', _kCFStringEncodingUTF8
    )
    _prop_key_source_id = lib.CFStringCreateWithCString(
        None, b'TISPropertyInputSourceID', _kCFStringEncodingUTF8
    )

    return _carbon


def keycode_to_char(keycode: int) -> str | None:
    """Translate a keycode to a character using the currently active keyboard layout.

    Uses TISCopyCurrentKeyboardInputSource + UCKeyTranslate, which is the same
    mechanism the OS uses for text fields — always in sync with what the user sees.
    """
    carbon = _get_carbon()
    if not carbon or not _prop_key_layout_data:
        return None
    try:
        source = carbon.TISCopyCurrentKeyboardInputSource()
        if not source:
            return None

        layout_data = carbon.TISGetInputSourceProperty(source, _prop_key_layout_data)
        if not layout_data:
            carbon.CFRelease(source)
            return None

        layout_ptr = carbon.CFDataGetBytePtr(layout_data)
        dead_key_state = ctypes.c_uint32(0)
        actual_len = ctypes.c_long(0)
        unicode_buf = ctypes.create_unicode_buffer(4)

        carbon.UCKeyTranslate(
            layout_ptr,
            keycode,
            0,  # kUCKeyActionDown
            0,  # no modifiers
            0,  # default keyboard type
            0,  # kUCKeyTranslateNoDeadKeysBit
            ctypes.byref(dead_key_state),
            4,
            ctypes.byref(actual_len),
            unicode_buf,
        )

        carbon.CFRelease(source)

        length = actual_len.value
        if length > 0:
            return unicode_buf.value[:length]
        return None
    except Exception:
        return None


def switch_layout_tis(lang: str) -> None:
    """Switch input layout to the given language code ('ru', 'uk', 'en').

    TISSelectInputSource must be called from the main thread.
    If called from a background thread, dispatches to main thread synchronously.
    """
    if threading.current_thread() is not threading.main_thread():
        _dispatch_to_main(lang)
        return
    _switch_layout_tis_main(lang)


def _dispatch_to_main(lang: str) -> None:
    """Dispatch layout switch to main thread via PyObjC NSObject mechanism."""
    try:
        _switcher.performSelectorOnMainThread_withObject_waitUntilDone_(
            b'switchLayout:', lang, True
        )
    except Exception as e:
        print(f'[layout] main thread dispatch failed ({e}), calling directly')
        _switch_layout_tis_main(lang)


def _init_switcher():
    from Foundation import NSObject

    class _Switcher(NSObject):
        def switchLayout_(self, lang_str):
            _switch_layout_tis_main(lang_str)

    return _Switcher.alloc().init()


try:
    _switcher = _init_switcher()
except Exception:
    _switcher = None


def _switch_layout_tis_main(lang: str) -> bool:
    """Internal: must be called from main thread."""
    target_ids = _LANG_TO_IDS.get(lang)
    if not target_ids:
        return False

    carbon = _get_carbon()
    if not carbon or not _prop_key_source_id:
        return False

    try:
        source_list = carbon.TISCreateInputSourceList(None, False)
        count = carbon.CFArrayGetCount(source_list)

        for i in range(count):
            source = carbon.CFArrayGetValueAtIndex(source_list, i)
            prop = carbon.TISGetInputSourceProperty(source, _prop_key_source_id)
            if not prop:
                continue
            buf = ctypes.create_string_buffer(256)
            if carbon.CFStringGetCString(prop, buf, 256, _kCFStringEncodingUTF8):
                if buf.value in target_ids:
                    carbon.TISSelectInputSource(source)
                    carbon.CFRelease(source_list)
                    return True

        carbon.CFRelease(source_list)
        return False
    except Exception as e:
        print(f'Layout switch failed: {e}')
        return False
