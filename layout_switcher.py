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
