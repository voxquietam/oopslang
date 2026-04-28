"""
Global keyboard event listener via CGEventTap (Core Graphics).
Requires Accessibility permission: System Settings -> Privacy & Security -> Accessibility.
"""

import threading
from typing import Callable

import Quartz
from word_detector import WordBuffer, SEPARATORS, PUNCTUATION
from text_replacer import replace_word


# CGEventTap callback type
EventCallback = Callable[[str, bool], None]


class KeyListener:
    def __init__(self, word_buffer: WordBuffer):
        self.word_buffer = word_buffer
        self._tap = None
        self._run_loop_source = None
        self._thread = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._tap:
            Quartz.CGEventTapEnable(self._tap, False)

    def _run(self) -> None:
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

    def _callback(self, proxy, event_type, event, refcon):
        if event_type != Quartz.kCGEventKeyDown:
            return event

        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        char = _keycode_to_char(event)

        if char is None:
            return event

        if char in SEPARATORS:
            # Space or newline — check if word needs correction
            word = self.word_buffer.word
            needs_fix, correct_word = self.word_buffer.check_wrong_layout()
            self.word_buffer.clear()

            if needs_fix:
                # Let the space event pass through first, then replace
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
