"""
oopslang — auto-correct wrong keyboard layout on macOS.
Detects when words are typed in the wrong layout and fixes them on Space.

Requires: Accessibility permission in System Settings -> Privacy & Security -> Accessibility.
"""

import sys
from pathlib import Path

from app import OopslangApp, _acquire_lock, _release_lock

_LOG_PATH = Path.home() / 'Library' / 'Logs' / 'oopslang.log'


def main():
    if not _acquire_lock():
        return

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log = open(_LOG_PATH, 'a', encoding='utf-8', buffering=1)
    sys.stdout = log
    sys.stderr = log

    try:
        OopslangApp().run()
    finally:
        _release_lock()
        log.close()


if __name__ == '__main__':
    main()
