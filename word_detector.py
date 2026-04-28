"""
Current word buffer + wrong layout detection.
Logic:
  - Accumulate characters since the last separator (space, newline, punctuation).
  - On space: try converting the word via each language's mapping and check its dictionary.
    First match wins.
"""

from keymap import transliterate

SEPARATORS = {' ', '\n', '\r', '\t'}
PUNCTUATION = {'.', ',', '!', '?', ';', ':', '-', '(', ')', '"', "'"}


class WordBuffer:
    def __init__(self, dictionaries: dict[str, set[str]]):
        self.dictionaries = dictionaries  # {lang: set_of_words}
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
        Returns (needs_correction, correct_word, lang).
        Tries all loaded languages. First match wins.
        """
        word = self.word
        if not word:
            return False, '', ''

        for lang, words in self.dictionaries.items():
            if word.lower() in words:
                return False, '', ''

            converted = transliterate(word, lang)
            if converted != word and converted.lower() in words:
                return True, converted, lang

        return False, '', ''
