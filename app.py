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

import exceptions as exc_store
from word_detector import WordBuffer
from key_listener import KeyListener

_LOCK_FILE = Path.home() / '.cache' / 'oopslang' / 'oopslang.lock'


def _osascript_input(title: str, message: str) -> str | None:
    """Show a native input dialog via osascript. Returns text or None if cancelled."""
    script = (
        f'display dialog {_osa_str(message)} '
        f'default answer "" '
        f'with title {_osa_str(title)} '
        f'buttons {{"Cancel", "OK"}} '
        f'default button "OK"'
    )
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    # output: "button returned:OK, text returned:hello"
    for part in result.stdout.strip().split(', '):
        if part.startswith('text returned:'):
            return part[len('text returned:'):].strip() or None
    return None


def _osascript_alert(title: str, message: str, buttons: list[str] | None = None) -> str:
    """Show a native alert via osascript. Returns the button label clicked."""
    if buttons is None:
        buttons = ['OK']
    btn_list = '{' + ', '.join(_osa_str(b) for b in buttons) + '}'
    script = (
        f'display alert {_osa_str(title)} '
        f'message {_osa_str(message)} '
        f'buttons {btn_list} '
        f'default button {_osa_str(buttons[-1])}'
    )
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    out = result.stdout.strip()
    # output: "button returned:Close"
    if out.startswith('button returned:'):
        return out[len('button returned:'):]
    return ''


def _osascript_choose(title: str, prompt: str, items: list[str]) -> str | None:
    """Show a native list picker. Returns selected item or None if cancelled."""
    items_osa = '{' + ', '.join(_osa_str(i) for i in items) + '}'
    script = (
        f'choose from list {items_osa} '
        f'with title {_osa_str(title)} '
        f'with prompt {_osa_str(prompt)} '
        f'OK button name "Remove" '
        f'cancel button name "Cancel" '
        f'multiple selections allowed false'
    )
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    out = result.stdout.strip()
    return out if out and out != 'false' else None


def _osa_str(s: str) -> str:
    """Escape a string for AppleScript."""
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
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
        icon_path = str(Path(__file__).parent / 'icon.png')
        super().__init__('', icon=icon_path, template=True, quit_button=None)

        self._exceptions = exc_store.load()
        self._word_buffer = WordBuffer(exceptions=self._exceptions)
        self._listener = KeyListener(self._word_buffer)

        self._toggle_item = rumps.MenuItem('Enabled', callback=self.toggle_active)
        self._toggle_item.state = True

        self.menu = [
            self._toggle_item,
            None,
            rumps.MenuItem('Settings...', callback=self.open_settings),
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

    def open_settings(self, _sender):
        from settings_window import open_settings
        open_settings(
            word_buffer=self._word_buffer,
            listener=self._listener,
            toggle_item=self._toggle_item,
            exceptions=self._exceptions,
            on_exceptions_change=lambda e: exc_store.save(e),
        )

    def quit_app(self, _sender):
        self._listener.stop()
        rumps.quit_application()
