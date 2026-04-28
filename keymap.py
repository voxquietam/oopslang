# Key mappings: typed in EN layout -> intended character in target layout
# Based on standard QWERTY <-> national keyboard layouts

LAYOUTS: dict[str, dict[str, str]] = {
    'ru': {
        'q': 'й', 'w': 'ц', 'e': 'у', 'r': 'к', 't': 'е',
        'y': 'н', 'u': 'г', 'i': 'ш', 'o': 'щ', 'p': 'з',
        '[': 'х', ']': 'ъ',
        'a': 'ф', 's': 'ы', 'd': 'в', 'f': 'а', 'g': 'п',
        'h': 'р', 'j': 'о', 'k': 'л', 'l': 'д', ';': 'ж',
        "'": 'э',
        'z': 'я', 'x': 'ч', 'c': 'с', 'v': 'м', 'b': 'и',
        'n': 'т', 'm': 'ь', ',': 'б', '.': 'ю', '/': '.',

        'Q': 'Й', 'W': 'Ц', 'E': 'У', 'R': 'К', 'T': 'Е',
        'Y': 'Н', 'U': 'Г', 'I': 'Ш', 'O': 'Щ', 'P': 'З',
        '{': 'Х', '}': 'Ъ',
        'A': 'Ф', 'S': 'Ы', 'D': 'В', 'F': 'А', 'G': 'П',
        'H': 'Р', 'J': 'О', 'K': 'Л', 'L': 'Д', ':': 'Ж',
        '"': 'Э',
        'Z': 'Я', 'X': 'Ч', 'C': 'С', 'V': 'М', 'B': 'И',
        'N': 'Т', 'M': 'Ь', '<': 'Б', '>': 'Ю', '?': ',',
    },
    'uk': {
        'q': 'й', 'w': 'ц', 'e': 'у', 'r': 'к', 't': 'е',
        'y': 'н', 'u': 'г', 'i': 'ш', 'o': 'щ', 'p': 'з',
        '[': 'х', ']': 'ї',
        'a': 'ф', 's': 'і', 'd': 'в', 'f': 'а', 'g': 'п',
        'h': 'р', 'j': 'о', 'k': 'л', 'l': 'д', ';': 'ж',
        "'": 'є',
        'z': 'я', 'x': 'ч', 'c': 'с', 'v': 'м', 'b': 'и',
        'n': 'т', 'm': 'ь', ',': 'б', '.': 'ю', '/': '.',

        'Q': 'Й', 'W': 'Ц', 'E': 'У', 'R': 'К', 'T': 'Е',
        'Y': 'Н', 'U': 'Г', 'I': 'Ш', 'O': 'Щ', 'P': 'З',
        '{': 'Х', '}': 'Ї',
        'A': 'Ф', 'S': 'І', 'D': 'В', 'F': 'А', 'G': 'П',
        'H': 'Р', 'J': 'О', 'K': 'Л', 'L': 'Д', ':': 'Ж',
        '"': 'Є',
        'Z': 'Я', 'X': 'Ч', 'C': 'С', 'V': 'М', 'B': 'И',
        'N': 'Т', 'M': 'Ь', '<': 'Б', '>': 'Ю', '?': ',',
    },
}


def transliterate(text: str, lang: str) -> str:
    """Convert text from EN layout to target lang layout."""
    mapping = LAYOUTS.get(lang, {})
    return ''.join(mapping.get(ch, ch) for ch in text)


def transliterate_to_en(text: str, lang: str) -> str:
    """Convert text from lang layout back to EN."""
    mapping = {v: k for k, v in LAYOUTS.get(lang, {}).items()}
    return ''.join(mapping.get(ch, ch) for ch in text)
