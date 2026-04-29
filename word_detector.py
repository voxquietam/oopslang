"""
Current word buffer + wrong layout detection.
Logic:
  - Accumulate characters since the last separator (space, newline, punctuation).
  - On space: check all possible layout conversions.
    Short words: pick first match from corpus word list.
    Long words: pick the conversion with the highest bigram score gain.
"""

from keymap import transliterate, transliterate_to_en, transliterate_cross
from scorer import should_convert, score, is_known_word, SHORT_WORD_MAX_LEN

SEPARATORS = {' ', '\n', '\r', '\t'}
# Only chars that cannot be part of a mistyped word.
# Chars like ' , . ; are excluded because they map to Cyrillic letters (э, б, ю, ж).
PUNCTUATION = {'!', '?', '(', ')', '"', '.'}

# Characters exclusive to one Cyrillic language — strong layout signal.
_LANG_EXCLUSIVE: dict[str, frozenset[str]] = {
    'ru': frozenset('ыъэЫЪЭ'),
    'uk': frozenset('іїєІЇЄ'),
}

_LANGS = ['ru', 'uk']


_EN_LAYOUT_CHARS = frozenset('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ[]{}\'";:/?.>,<')


def _is_letters_only(word: str) -> bool:
    """Return True if word looks like valid EN layout input (letters + layout-mapped chars)."""
    return all(ch in _EN_LAYOUT_CHARS for ch in word)


def _has_cyrillic(word: str) -> bool:
    """Return True if word contains at least one Cyrillic character."""
    return any('\u0400' <= ch <= '\u04FF' for ch in word)


class WordBuffer:
    def __init__(self, exceptions: set[str] | None = None):
        self._buffer: list[str] = []
        self._exceptions: set[str] = exceptions or set()

    def set_exceptions(self, exceptions: set[str]) -> None:
        self._exceptions = exceptions

    def push(self, char: str) -> None:
        self._buffer.append(char)

    def pop(self) -> None:
        if self._buffer:
            self._buffer.pop()

    def clear(self) -> None:
        self._buffer.clear()

    @property
    def word(self) -> str:
        return ''.join(self._buffer)

    def check_wrong_layout(self) -> tuple[bool, str, str]:
        """
        Returns (needs_correction, correct_word, target_lang).
        Short words: first match wins.
        Long words: best scoring conversion wins.
        Hyphenated words: each part checked independently; all parts must agree on lang.
        """
        word = self.word
        if not word:
            return False, '', ''

        if word.lower() in self._exceptions:
            return False, '', ''

        if '-' in word:
            return self._check_hyphenated(word)
        if len(word) <= SHORT_WORD_MAX_LEN:
            return self._check_short(word)
        return self._check_long(word)

    def _check_hyphenated(self, word: str) -> tuple[bool, str, str]:
        parts = word.split('-')
        results = []
        for part in parts:
            if not part:
                results.append((False, part, ''))
                continue
            if len(part) <= SHORT_WORD_MAX_LEN:
                r = self._check_short(part)
            else:
                r = self._check_long(part, allow_particles=True)
            results.append(r)

        # All convertible parts must agree on the target language.
        langs = {r[2] for r in results if r[0]}
        if not langs or len(langs) > 1:
            return False, '', ''

        target_lang = langs.pop()
        converted_parts = [r[1] if r[0] else p for r, p in zip(results, parts)]
        return True, '-'.join(converted_parts), target_lang

    def _check_short(self, word: str) -> tuple[bool, str, str]:
        candidates: list[tuple[float, str, str]] = []

        for lang in _LANGS:
            converted = transliterate(word, lang)
            if converted != word and should_convert(word, converted, lang, 'en'):
                candidates.append((score(converted, lang), converted, lang))

            converted_en = transliterate_to_en(word, lang)
            if (converted_en != word
                    and _is_letters_only(converted_en)
                    and should_convert(word, converted_en, 'en', lang)):
                candidates.append((score(converted_en, 'en'), converted_en, 'en'))

        # Cross-layout: e.g. RU→UK or UK→RU (only for Cyrillic input)
        if _has_cyrillic(word):
            for from_lang in _LANGS:
                for to_lang in _LANGS:
                    if from_lang == to_lang:
                        continue
                    converted = transliterate_cross(word, from_lang, to_lang)
                    if converted == word:
                        continue
                    if should_convert(word, converted, to_lang, from_lang):
                        candidates.append((score(converted, to_lang), converted, to_lang))
                    elif (is_known_word(word, from_lang)
                          and is_known_word(converted, to_lang)
                          and _LANG_EXCLUSIVE['ru'].intersection(converted)):
                        # Converted word contains RU-exclusive chars (ы/ъ/э).
                        # Only check RU-exclusive chars to avoid false RU→UK swaps
                        # (e.g. «ты»→«ті» would incorrectly fire for UK-exclusive 'і').
                        candidates.append((score(converted, to_lang), converted, to_lang))

        if candidates:
            _lang_priority = {'ru': 0, 'uk': 1, 'en': 2}
            # Small score bonus to prefer RU over UK in ambiguous cases.
            _lang_bonus = {'ru': 1.0, 'uk': 0.0, 'en': 0.0}
            # Deduplicate: same converted word in multiple langs → keep highest-priority lang.
            best_per_word: dict[str, tuple[float, str, str]] = {}
            for sc, w, lang in candidates:
                if w not in best_per_word:
                    best_per_word[w] = (sc, w, lang)
                else:
                    existing = best_per_word[w]
                    if _lang_priority.get(lang, 9) < _lang_priority.get(existing[2], 9):
                        best_per_word[w] = (sc, w, lang)
            candidates = list(best_per_word.values())
            candidates.sort(key=lambda x: x[0] + _lang_bonus.get(x[2], 0), reverse=True)
            _, best_word, best_lang = candidates[0]
            return True, best_word, best_lang

        return False, '', ''

    def _check_long(self, word: str, allow_particles: bool = False) -> tuple[bool, str, str]:
        best_gain = 0.0
        best_word = ''
        best_lang = ''

        for lang in _LANGS:
            converted = transliterate(word, lang)
            if converted != word and should_convert(word, converted, lang, 'en'):
                gain = score(converted, lang) - score(word, 'en')
                if gain > best_gain:
                    best_gain, best_word, best_lang = gain, converted, lang

            converted_en = transliterate_to_en(word, lang)
            if (converted_en != word
                    and _is_letters_only(converted_en)
                    and not any(is_known_word(word, l) for l in _LANGS)
                    and should_convert(word, converted_en, 'en', lang)):
                gain = score(converted_en, 'en') - score(word, lang)
                if gain > best_gain:
                    best_gain, best_word, best_lang = gain, converted_en, 'en'

        # Cross-layout: e.g. RU→UK or UK→RU (only for Cyrillic input)
        if _has_cyrillic(word):
            for from_lang in _LANGS:
                for to_lang in _LANGS:
                    if from_lang == to_lang:
                        continue
                    converted = transliterate_cross(word, from_lang, to_lang)
                    if converted == word:
                        continue
                    if (should_convert(word, converted, to_lang, from_lang)
                            and is_known_word(converted, to_lang, allow_particles)):
                        gain = score(converted, to_lang) - score(word, from_lang)
                        if gain > best_gain:
                            best_gain, best_word, best_lang = gain, converted, to_lang
                    elif not best_word and is_known_word(converted, to_lang, allow_particles):
                        if (not is_known_word(word, from_lang)
                                or _LANG_EXCLUSIVE['ru'].intersection(converted)):
                            # Dictionary confirms target, or converted has RU-exclusive chars.
                            best_word, best_lang = converted, to_lang

        if best_word:
            # Dictionary tiebreak: if bigrams picked lang X but only lang Y's dictionary
            # knows the word, prefer Y (e.g. насамперед: bigrams→ru, dict→uk).
            if best_lang in _LANGS and not is_known_word(best_word, best_lang, allow_particles):
                for lang in _LANGS:
                    if lang != best_lang and is_known_word(best_word, lang, allow_particles):
                        return True, best_word, lang
            return True, best_word, best_lang

        # Vocabulary check: word is already Cyrillic but known only in one language.
        # Switch layout without replacing text (e.g. насамперед typed in RU layout).
        known_in = [l for l in _LANGS if is_known_word(word, l, allow_particles)]
        if len(known_in) == 1:
            return True, word, known_in[0]

        return False, '', ''
