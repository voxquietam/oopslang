"""
Current word buffer + wrong layout detection.
Logic:
  - Accumulate characters since the last separator (space, newline, punctuation).
  - On space: score the word in each language using bigram frequencies.
    If the converted version scores higher than the original → wrong layout.
"""

from keymap import transliterate, transliterate_to_en
from scorer import should_convert

SEPARATORS = {' ', '\n', '\r', '\t'}
PUNCTUATION = {'.', ',', '!', '?', ';', ':', '-', '(', ')', '"', "'"}

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
        Tries EN→lang and lang→EN for all supported languages.
        """
        word = self.word
        if not word:
            return False, '', ''

        for lang in _LANGS:
            # EN layout → lang (e.g. ghbdtn → привет)
            converted = transliterate(word, lang)
            if converted != word and should_convert(word, converted, lang, 'en'):
                return True, converted, lang

            # lang layout → EN (e.g. руддщ → hello)
            converted_en = transliterate_to_en(word, lang)
            if converted_en != word and should_convert(word, converted_en, 'en', lang):
                return True, converted_en, 'en'

        return False, '', ''
