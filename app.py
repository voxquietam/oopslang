"""
oopslang menu bar app.
Runs CGEventTap in a background thread; rumps occupies the main thread.
"""

import os
import plistlib
import subprocess
import sys
import threading
from pathlib import Path

import rumps

from word_detector import WordBuffer
from key_listener import KeyListener

_LOCK_FILE = Path.home() / '.cache' / 'oopslang' / 'oopslang.lock'
_PLIST_LABEL = 'com.oopslang.app'
_PLIST_PATH = Path.home() / 'Library' / 'LaunchAgents' / f'{_PLIST_LABEL}.plist'


def _acquire_lock() -> bool:
    """Write PID to lock file. Returns False if another instance is already running."""
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _LOCK_FILE.exists():
        try:
            pid = int(_LOCK_FILE.read_text().strip())
            # Check if the process is still alive
            os.kill(pid, 0)
            return False  # Process exists — another instance is running
        except (ProcessLookupError, ValueError):
            pass  # Stale lock — process is dead, take over
    _LOCK_FILE.write_text(str(os.getpid()))
    return True


def _release_lock() -> None:
    _LOCK_FILE.unlink(missing_ok=True)


def _login_agent_installed() -> bool:
    return _PLIST_PATH.exists()


def _install_login_agent() -> None:
    python = sys.executable
    script = str(Path(__file__).resolve().parent / 'main.py')
    plist = {
        'Label': _PLIST_LABEL,
        'ProgramArguments': [python, script],
        'RunAtLoad': True,
        'KeepAlive': False,
        'StandardOutPath': str(Path.home() / 'Library' / 'Logs' / 'oopslang.log'),
        'StandardErrorPath': str(Path.home() / 'Library' / 'Logs' / 'oopslang.log'),
    }
    _PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_PLIST_PATH, 'wb') as f:
        plistlib.dump(plist, f)
    subprocess.run(['launchctl', 'load', str(_PLIST_PATH)], capture_output=True)


def _uninstall_login_agent() -> None:
    subprocess.run(['launchctl', 'unload', str(_PLIST_PATH)], capture_output=True)
    _PLIST_PATH.unlink(missing_ok=True)


class OopslangApp(rumps.App):
    def __init__(self):
        super().__init__('Oopslang', quit_button=None)

        self._word_buffer = WordBuffer()
        self._listener = KeyListener(self._word_buffer)

        self._toggle_item = rumps.MenuItem('Enabled', callback=self.toggle_active)
        self._toggle_item.state = True

        self._login_item = rumps.MenuItem('Launch at Login', callback=self.toggle_login)
        self._login_item.state = _login_agent_installed()

        self.menu = [
            self._toggle_item,
            self._login_item,
            None,
            rumps.MenuItem('Quit', callback=self.quit_app),
        ]

        self._listener_thread = threading.Thread(
            target=self._listener.run,
            daemon=True,
            name='KeyListener',
        )
        self._listener_thread.start()

    def toggle_active(self, sender):
        active = not self._listener.is_active()
        self._listener.set_active(active)
        sender.state = active
        self.title = 'Oopslang' if active else 'Oopslang (paused)'

    def toggle_login(self, sender):
        if _login_agent_installed():
            _uninstall_login_agent()
        else:
            _install_login_agent()
        sender.state = _login_agent_installed()

    def quit_app(self, _sender):
        self._listener.stop()
        rumps.quit_application()
