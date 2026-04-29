"""
Text replacement: delete current word and insert corrected version.
Uses CGEventCreateKeyboardEvent to simulate backspaces, then pastes via clipboard.
"""

import time
import subprocess


def replace_word_with_suffix(old_word: str, new_word: str, suffix: str) -> None:
    """Like replace_word but triggered by punctuation: delete word+suffix, paste new_word+suffix."""
    delete_count = len(old_word) + len(suffix)
    try:
        _replace_via_pyobjc(delete_count, new_word, trailing=suffix)
    except Exception as e:
        print(f'[replace] pyobjc failed ({e}), using applescript fallback')
        _replace_via_applescript(delete_count, new_word + suffix)


def replace_word(old_word: str, new_word: str) -> None:
    """
    Delete old_word (via backspaces) and type new_word.
    Called right after space is pressed — we delete the word + the space,
    then insert corrected word + space.
    """
    delete_count = len(old_word) + 1  # +1 for the space we just pressed

    try:
        _replace_via_pyobjc(delete_count, new_word)
    except Exception as e:
        print(f'[replace] pyobjc failed ({e}), using applescript fallback')
        _replace_via_applescript(delete_count, new_word)


def _replace_via_pyobjc(delete_count: int, new_word: str, trailing: str = ' ') -> None:
    import Quartz

    # Wait for the triggering space/separator event to be processed by the OS
    # before we start deleting, to avoid race conditions.
    time.sleep(0.05)

    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)

    # Key code 51 = Backspace
    # Post at kCGAnnotatedSessionEventTap so our own event tap does not see these events.
    for _ in range(delete_count):
        down = Quartz.CGEventCreateKeyboardEvent(src, 51, True)
        up = Quartz.CGEventCreateKeyboardEvent(src, 51, False)
        Quartz.CGEventPost(Quartz.kCGAnnotatedSessionEventTap, down)
        Quartz.CGEventPost(Quartz.kCGAnnotatedSessionEventTap, up)

    # Paste the corrected word + trailing char via clipboard
    _paste_text(new_word + trailing)


def _paste_text(text: str) -> None:
    """Put text in clipboard and simulate Cmd+V."""
    import Quartz
    from AppKit import NSPasteboard, NSStringPboardType

    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSStringPboardType)

    time.sleep(0.05)

    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    # Key code 9 = V, with Cmd flag
    cmd_flag = Quartz.kCGEventFlagMaskCommand
    down = Quartz.CGEventCreateKeyboardEvent(src, 9, True)
    Quartz.CGEventSetFlags(down, cmd_flag)
    up = Quartz.CGEventCreateKeyboardEvent(src, 9, False)
    Quartz.CGEventSetFlags(up, cmd_flag)
    Quartz.CGEventPost(Quartz.kCGAnnotatedSessionEventTap, down)
    Quartz.CGEventPost(Quartz.kCGAnnotatedSessionEventTap, up)


def _replace_via_applescript(delete_count: int, new_word: str) -> None:
    """Fallback: use AppleScript for backspaces, clipboard for paste."""
    # Put text in clipboard via pbcopy (no key events generated).
    subprocess.run(['pbcopy'], input=(new_word + ' ').encode('utf-8'), check=True)
    # Send backspaces via AppleScript.
    backspaces = 'key code 51\n' * delete_count
    script = f'''tell application "System Events"
        {backspaces}
    end tell'''
    subprocess.run(['osascript', '-e', script], capture_output=True)
    # Paste via Cmd+V (filtered by our tap).
    script2 = '''tell application "System Events"
        keystroke "v" using command down
    end tell'''
    subprocess.run(['osascript', '-e', script2], capture_output=True)
