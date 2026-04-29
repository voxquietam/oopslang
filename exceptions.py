"""
User-defined word exceptions: words that should never be auto-corrected.
Persisted to ~/.config/oopslang/exceptions.json.
"""

import json
from pathlib import Path

_CONFIG_PATH = Path.home() / '.config' / 'oopslang' / 'exceptions.json'


def load() -> set[str]:
    if not _CONFIG_PATH.exists():
        return set()
    try:
        return set(json.loads(_CONFIG_PATH.read_text(encoding='utf-8')))
    except Exception:
        return set()


def save(words: set[str]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(
        json.dumps(sorted(words), ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
