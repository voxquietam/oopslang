"""
Bigram-based language scorer.
Scores a word by summing log-probabilities of consecutive character pairs.
Used to detect if a word was typed in the wrong layout.

Run build_bigrams.py once to generate data/bigrams.json.
"""

import json
import math
from pathlib import Path

_BIGRAMS_PATH = Path(__file__).parent / 'data' / 'bigrams.json'
_DEFAULT_PROB = 1e-6
_MIN_WORD_LEN = 3

_bigrams: dict[str, dict[str, float]] = {}


def _load() -> None:
    global _bigrams
    if not _BIGRAMS_PATH.exists():
        print(
            'WARNING: data/bigrams.json not found. '
            'Run python build_bigrams.py to generate it.'
        )
        return
    with open(_BIGRAMS_PATH, encoding='utf-8') as f:
        _bigrams = json.load(f)
    langs = ', '.join(_bigrams.keys())
    print(f'Loaded bigrams for: {langs}')


_load()


def score(word: str, lang: str) -> float:
    """Log-probability score of word in given language. Higher = more likely."""
    table = _bigrams.get(lang, {})
    word = word.lower()
    if len(word) < 2:
        return 0.0
    total = 0.0
    for i in range(len(word) - 1):
        pair = word[i:i + 2]
        prob = table.get(pair, _DEFAULT_PROB)
        total += math.log(prob)
    return total


def should_convert(original: str, converted: str, target_lang: str, source_lang: str) -> bool:
    """Returns True if converted scores better in target_lang than original in source_lang."""
    if len(original) < _MIN_WORD_LEN:
        return False
    return score(converted, target_lang) > score(original, source_lang)
