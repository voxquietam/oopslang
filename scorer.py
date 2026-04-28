"""
Bigram-based language scorer.
For short words (< 5 chars): checks against corpus-extracted frequent word list.
For longer words: compares bigram log-probability scores.

Run build_bigrams.py once to generate data/bigrams.json.
"""

import json
import math
from pathlib import Path

_BIGRAMS_PATH = Path(__file__).parent / 'data' / 'bigrams.json'
_DEFAULT_PROB = 1e-6
SHORT_WORD_MAX_LEN = 4
THRESHOLD_PER_CHAR = 0.8

_bigrams: dict[str, dict[str, float]] = {}
_short_words: dict[str, set[str]] = {}


def _load() -> None:
    global _bigrams, _short_words
    if not _BIGRAMS_PATH.exists():
        print('WARNING: data/bigrams.json not found. Run build_bigrams.py to generate it.')
        return
    with open(_BIGRAMS_PATH, encoding='utf-8') as f:
        data = json.load(f)

    for lang, payload in data.items():
        if isinstance(payload, dict) and 'bigrams' in payload:
            _bigrams[lang] = payload['bigrams']
            _short_words[lang] = set(payload.get('short_words', []))
        else:
            # Legacy format (flat bigram dict)
            _bigrams[lang] = payload

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


def is_known_short_word(word: str, lang: str) -> bool:
    return word.lower() in _short_words.get(lang, set())


def should_convert(original: str, converted: str, target_lang: str, source_lang: str) -> bool:
    """
    Returns True if original looks wrong in source_lang and converted looks right in target_lang.
    Short words: check corpus-extracted word lists.
    Long words: compare bigram scores.
    """
    if len(original) < 1:
        return False

    if len(original) <= SHORT_WORD_MAX_LEN:
        return (
            not is_known_short_word(original, source_lang)
            and is_known_short_word(converted, target_lang)
        )

    gain = score(converted, target_lang) - score(original, source_lang)
    return gain / len(original) > THRESHOLD_PER_CHAR
