"""
oopslang — auto-correct wrong keyboard layout on macOS.
Detects when words are typed in the wrong layout and fixes them on Space.

Requires: Accessibility permission in System Settings -> Privacy & Security -> Accessibility.
"""

from app import OopslangApp, _acquire_lock, _release_lock


def main():
    if not _acquire_lock():
        print('oopslang is already running, exiting.')
        return
    try:
        OopslangApp().run()
    finally:
        _release_lock()


if __name__ == '__main__':
    main()
