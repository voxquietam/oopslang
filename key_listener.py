"""
Global keyboard event listener via CGEventTap (Core Graphics).
Requires Accessibility permission: System Settings -> Privacy & Security -> Accessibility.

Must be run on the main thread so that TISSelectInputSource works correctly.
"""

import threading

import Quartz
from word_detector import WordBuffer, SEPARATORS, PUNCTUATION
from text_replacer import replace_word
from layout_switcher import switch_layout_tis


class KeyListener:
    def __init__(self, word_buffer: WordBuffer):
        self.word_buffer = word_buffer
        self._tap = None

    def run(self) -> None:
        """Start listening. Blocks the calling thread (must be main thread)."""
        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown),
            self._callback,
            None,
        )

        if tap is None:
            print(
                'ERROR: Could not create event tap.\n'
                'Grant Accessibility permission in System Settings -> Privacy & Security -> Accessibility.'
            )
            return

        self._tap = tap
        run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            run_loop_source,
            Quartz.kCFRunLoopCommonModes,
        )
        Quartz.CGEventTapEnable(tap, True)
        Quartz.CFRunLoopRun()

    def stop(self) -> None:
        if self._tap:
            Quartz.CGEventTapEnable(self._tap, False)
        Quartz.CFRunLoopStop(Quartz.CFRunLoopGetMain())

    def _callback(self, proxy, event_type, event, refcon):
        if event_type != Quartz.kCGEventKeyDown:
            return event

        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        char = _keycode_to_char(event)

        if char is None:
            return event

        if char in SEPARATORS:
            word = self.word_buffer.word
            needs_fix, correct_word, lang = self.word_buffer.check_wrong_layout()
            self.word_buffer.clear()

            if needs_fix:
                # Switch layout on main thread (we're in CFRunLoop callback = main thread)
                switch_layout_tis(lang)
                # Replace word in background (needs delay for clipboard)
                threading.Thread(
                    target=replace_word,
                    args=(word, correct_word),
                    daemon=True,
                ).start()
        elif char == '\x08' or keycode == 51:
            # Backspace
            self.word_buffer.pop()
        elif char in PUNCTUATION:
            self.word_buffer.clear()
        else:
            self.word_buffer.push(char)

        return event


def _keycode_to_char(event) -> str | None:
    """Extract typed character from CGEvent."""
    try:
        char = Quartz.CGEventKeyboardGetUnicodeString(event, 1, None, None)
        if char:
            return char[1] if isinstance(char, tuple) else char
    except Exception:
        pass
    return None
