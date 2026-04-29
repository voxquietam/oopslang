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
        super().__init__('Oopslang', quit_button=None)

        self._exceptions = exc_store.load()
        self._word_buffer = WordBuffer(exceptions=self._exceptions)
        self._listener = KeyListener(self._word_buffer)

        self._toggle_item = rumps.MenuItem('Enabled', callback=self.toggle_active)
        self._toggle_item.state = True

        self._login_item = rumps.MenuItem('Launch at Login', callback=self.toggle_login)
        self._login_item.state = _login_agent_installed()

        self.menu = [
            self._toggle_item,
            self._login_item,
            None,
            rumps.MenuItem('Add Exception...', callback=self.add_exception),
            rumps.MenuItem('Exceptions...', callback=self.show_exceptions),
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

    def add_exception(self, _sender):
        self._listener.pause_tap()
        try:
            word = _osascript_input(
                title='Add Exception',
                message='Word will never be auto-corrected:',
            )
        finally:
            self._listener.resume_tap()
            self._toggle_item.state = True

        if word:
            self._exceptions.add(word.lower())
            exc_store.save(self._exceptions)
            self._word_buffer.set_exceptions(self._exceptions)

    def show_exceptions(self, _sender):
        if not self._exceptions:
            _osascript_alert('Exceptions', 'No exceptions added yet.')
            return
        lines = '\n'.join(sorted(self._exceptions))
        clicked = _osascript_alert(
            'Exceptions', lines, buttons=['Clear All', 'Close']
        )
        if clicked == 'Clear All':
            self._exceptions.clear()
            exc_store.save(self._exceptions)
            self._word_buffer.set_exceptions(self._exceptions)

    def toggle_login(self, sender):
        if _login_agent_installed():
            _uninstall_login_agent()
        else:
            _install_login_agent()
        sender.state = _login_agent_installed()

    def quit_app(self, _sender):
        self._listener.stop()
        rumps.quit_application()
