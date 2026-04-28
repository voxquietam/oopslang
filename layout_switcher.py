"""
Layout switching via TIS (Text Input Source) API using pure ctypes.
"""

import ctypes
import ctypes.util

_carbon = None

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

    _carbon = lib
    return _carbon


def keycode_to_char(keycode: int) -> str | None:
    """Translate a keycode to a character using the currently active keyboard layout.

    Uses TISCopyCurrentKeyboardInputSource + UCKeyTranslate, which is the same
    mechanism the OS uses for text fields — always in sync with what the user sees.
    """
    carbon = _get_carbon()
    if not carbon:
        return None
    try:
        lib_path = ctypes.util.find_library('Carbon')
        lib = ctypes.cdll.LoadLibrary(lib_path)

        lib.TISCopyCurrentKeyboardInputSource.restype = ctypes.c_void_p
        lib.TISCopyCurrentKeyboardInputSource.argtypes = []
        lib.TISGetInputSourceProperty.restype = ctypes.c_void_p
        lib.TISGetInputSourceProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        lib.CFDataGetBytePtr.restype = ctypes.c_void_p
        lib.CFDataGetBytePtr.argtypes = [ctypes.c_void_p]
        lib.UCKeyTranslate.restype = ctypes.c_int
        lib.UCKeyTranslate.argtypes = [
            ctypes.c_void_p,   # keyboardLayout
            ctypes.c_uint16,   # virtualKeyCode
            ctypes.c_uint16,   # keyAction
            ctypes.c_uint32,   # modifierKeyState
            ctypes.c_uint32,   # keyboardType
            ctypes.c_uint32,   # keyTranslateOptions
            ctypes.POINTER(ctypes.c_uint32),  # deadKeyState
            ctypes.c_long,     # maxStringLength
            ctypes.POINTER(ctypes.c_long),    # actualStringLength
            ctypes.c_wchar_p,  # unicodeString
        ]

        prop_key = carbon.CFStringCreateWithCString(
            None, b'TISPropertyUnicodeKeyLayoutData', _kCFStringEncodingUTF8
        )
        source = lib.TISCopyCurrentKeyboardInputSource()
        if not source:
            carbon.CFRelease(prop_key)
            return None

        layout_data = lib.TISGetInputSourceProperty(source, prop_key)
        if not layout_data:
            carbon.CFRelease(source)
            carbon.CFRelease(prop_key)
            return None

        layout_ptr = lib.CFDataGetBytePtr(layout_data)
        dead_key_state = ctypes.c_uint32(0)
        actual_len = ctypes.c_long(0)
        unicode_buf = ctypes.create_unicode_buffer(4)

        kUCKeyActionDown = 0
        kUCKeyTranslateNoDeadKeysBit = 0

        lib.UCKeyTranslate(
            layout_ptr,
            keycode,
            kUCKeyActionDown,
            0,   # no modifiers
            0,   # default keyboard type
            kUCKeyTranslateNoDeadKeysBit,
            ctypes.byref(dead_key_state),
            4,
            ctypes.byref(actual_len),
            unicode_buf,
        )

        carbon.CFRelease(source)
        carbon.CFRelease(prop_key)

        length = actual_len.value
        if length > 0:
            return unicode_buf.value[:length]
        return None
    except Exception:
        return None


def switch_layout_tis(lang: str) -> bool:
    """Switch input layout to the given language code ('ru', 'uk', 'en')."""
    target_ids = _LANG_TO_IDS.get(lang)
    if not target_ids:
        return False

    carbon = _get_carbon()
    if not carbon:
        return False

    try:
        prop_key = carbon.CFStringCreateWithCString(
            None, b'TISPropertyInputSourceID', _kCFStringEncodingUTF8
        )
        source_list = carbon.TISCreateInputSourceList(None, False)
        count = carbon.CFArrayGetCount(source_list)

        for i in range(count):
            source = carbon.CFArrayGetValueAtIndex(source_list, i)
            prop = carbon.TISGetInputSourceProperty(source, prop_key)
            if not prop:
                continue
            buf = ctypes.create_string_buffer(256)
            if carbon.CFStringGetCString(prop, buf, 256, _kCFStringEncodingUTF8):
                if buf.value in target_ids:
                    carbon.TISSelectInputSource(source)
                    carbon.CFRelease(source_list)
                    carbon.CFRelease(prop_key)
                    return True

        carbon.CFRelease(source_list)
        carbon.CFRelease(prop_key)
        return False
    except Exception as e:
        print(f'Layout switch failed: {e}')
        return False
