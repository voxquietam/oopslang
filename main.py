"""
oopslang — auto-correct wrong keyboard layout on macOS.
Detects when words are typed in the wrong layout and fixes them on Space.

Requires: Accessibility permission in System Settings -> Privacy & Security -> Accessibility.
"""

import signal
import sys

from word_detector import WordBuffer
from key_listener import KeyListener


def main():
    print('oopslang starting...')

    word_buffer = WordBuffer()
    listener = KeyListener(word_buffer)

    def _shutdown(sig, frame):
        print('\nStopping...')
        listener.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print('Listening. Press Ctrl+C to stop.')
    listener.run()  # blocks main thread with CFRunLoopRun


if __name__ == '__main__':
    main()
