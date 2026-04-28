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
PUNCTUATION = {'!', '?', ':', '-', '(', ')', '"'}

_LANGS = ['ru', 'uk']


class WordBuffer:
    def __init__(self):
        self._buffer: list[str] = []

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
        """
        word = self.word
        if not word:
            return False, '', ''

        if len(word) <= SHORT_WORD_MAX_LEN:
            return self._check_short(word)
        return self._check_long(word)

    def _check_short(self, word: str) -> tuple[bool, str, str]:
        for lang in _LANGS:
            converted = transliterate(word, lang)
            if converted != word and should_convert(word, converted, lang, 'en'):
                return True, converted, lang

            converted_en = transliterate_to_en(word, lang)
            if converted_en != word and should_convert(word, converted_en, 'en', lang):
                return True, converted_en, 'en'

        # Cross-layout: e.g. RU→UK or UK→RU
        for from_lang in _LANGS:
            for to_lang in _LANGS:
                if from_lang == to_lang:
                    continue
                converted = transliterate_cross(word, from_lang, to_lang)
                if converted != word and should_convert(word, converted, to_lang, from_lang):
                    return True, converted, to_lang

        return False, '', ''

    def _check_long(self, word: str) -> tuple[bool, str, str]:
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
            if converted_en != word and should_convert(word, converted_en, 'en', lang):
                gain = score(converted_en, 'en') - score(word, lang)
                if gain > best_gain:
                    best_gain, best_word, best_lang = gain, converted_en, 'en'

        # Cross-layout: e.g. RU→UK or UK→RU
        for from_lang in _LANGS:
            for to_lang in _LANGS:
                if from_lang == to_lang:
                    continue
                converted = transliterate_cross(word, from_lang, to_lang)
                if converted != word and should_convert(word, converted, to_lang, from_lang):
                    gain = score(converted, to_lang) - score(word, from_lang)
                    if gain > best_gain:
                        best_gain, best_word, best_lang = gain, converted, to_lang

        if best_word:
            # Dictionary tiebreak: if bigrams picked lang X but only lang Y's dictionary
            # knows the word, prefer Y (e.g. насамперед: bigrams→ru, dict→uk).
            if best_lang in _LANGS and not is_known_word(best_word, best_lang):
                for lang in _LANGS:
                    if lang != best_lang and is_known_word(best_word, lang):
                        return True, best_word, lang
            return True, best_word, best_lang

        # Vocabulary check: word is already Cyrillic but known only in one language.
        # Switch layout without replacing text (e.g. насамперед typed in RU layout).
        known_in = [l for l in _LANGS if is_known_word(word, l)]
        if len(known_in) == 1:
            return True, word, known_in[0]

        return False, '', ''
