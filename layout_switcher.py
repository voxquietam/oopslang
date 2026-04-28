"""
Layout switching via TIS (Text Input Source) from the Carbon framework.
"""

import subprocess


def get_current_layout() -> str:
    """Returns the current layout identifier, e.g. 'com.apple.keylayout.Russian'."""
    try:
        import Cocoa  # noqa: F401
        from Foundation import NSBundle  # noqa: F401
        result = subprocess.run(
            ['defaults', 'read', 'com.apple.HIToolbox', 'AppleCurrentKeyboardLayoutInputSourceID'],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception:
        return ''


def switch_to_layout(layout_id: str) -> bool:
    """
    Switches layout via AppleScript (reliable fallback, no code signing required).
    layout_id: e.g. 'Russian' or 'ABC'
    """
    script = f'''
    tell application "System Events"
        tell process "SystemUIServer"
            tell menu bar item 1 of menu bar 2
                click
                click menu item "{layout_id}" of menu 1
            end tell
        end tell
    end tell
    '''
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def switch_layout_tis(target: str = 'ru') -> bool:
    """
    Switches layout via TIS API (requires pyobjc).
    target: 'ru' or 'en'
    """
    try:
        from Carbon.framework import Carbon  # noqa: F401
    except ImportError:
        pass

    try:
        import ctypes
        import ctypes.util

        carbon_path = ctypes.util.find_library('Carbon')
        if not carbon_path:
            return False

        carbon = ctypes.cdll.LoadLibrary(carbon_path)

        # Low-level approach via ctypes, works without code signing
        carbon.TISCopyCurrentKeyboardInputSource.restype = ctypes.c_void_p
        current = carbon.TISCopyCurrentKeyboardInputSource()

        if target == 'ru':
            layout_ids = [b'com.apple.keylayout.Russian', b'com.apple.keylayout.Russian-PC']
        else:
            layout_ids = [b'com.apple.keylayout.ABC', b'com.apple.keylayout.US']

        # Get list of all input sources
        carbon.TISCreateInputSourceList.restype = ctypes.c_void_p
        source_list = carbon.TISCreateInputSourceList(None, False)

        from CoreFoundation import CFArrayGetCount, CFArrayGetValueAtIndex, CFRelease
        count = CFArrayGetCount(source_list)
        for i in range(count):
            source = CFArrayGetValueAtIndex(source_list, i)
            carbon.TISGetInputSourceProperty.restype = ctypes.c_void_p
            # kTISPropertyInputSourceID = CFSTR("TISPropertyInputSourceID")
            prop_id = carbon.TISGetInputSourceProperty(source, b'TISPropertyInputSourceID')
            if prop_id:
                from CoreFoundation import CFStringGetCString
                buf = ctypes.create_string_buffer(256)
                if CFStringGetCString(prop_id, buf, 256, 0x08000100):
                    if buf.value in layout_ids:
                        carbon.TISSelectInputSource(source)
                        CFRelease(source_list)
                        return True

        CFRelease(source_list)
        return False
    except Exception as e:
        print(f'TIS switch failed: {e}')
        return False
