"""
Dictionary loader for multiple languages.
Loads word lists from data/<lang>_words.txt. Falls back to built-in sets if files are not found.
"""

from pathlib import Path

_DATA_DIR = Path(__file__).parent / 'data'

_BUILTIN: dict[str, set[str]] = {
    'ru': {
        'привет', 'пока', 'да', 'нет', 'все', 'это', 'как', 'так', 'тут', 'там',
        'что', 'где', 'кто', 'нас', 'вас', 'мне', 'вам', 'ему', 'ей', 'они',
        'мы', 'вы', 'он', 'она', 'оно', 'и', 'в', 'на', 'по', 'за', 'от', 'из',
        'до', 'про', 'при', 'под', 'над', 'без', 'для', 'или', 'но', 'если',
        'когда', 'уже', 'еще', 'только', 'можно', 'надо', 'очень', 'хорошо',
        'плохо', 'много', 'мало', 'быстро', 'медленно', 'сейчас', 'потом',
        'здесь', 'всегда', 'никогда', 'иногда', 'снова', 'опять', 'просто',
    },
    'uk': {
        'привіт', 'поки', 'так', 'ні', 'все', 'це', 'як', 'тут', 'там',
        'що', 'де', 'хто', 'нас', 'вас', 'мені', 'вам', 'йому', 'їй', 'вони',
        'ми', 'ви', 'він', 'вона', 'воно', 'і', 'й', 'в', 'на', 'по', 'за',
        'від', 'з', 'із', 'до', 'про', 'при', 'під', 'над', 'без', 'для',
        'або', 'але', 'якщо', 'коли', 'вже', 'ще', 'тільки', 'можна', 'треба',
        'дуже', 'добре', 'погано', 'багато', 'мало', 'швидко', 'повільно',
        'зараз', 'потім', 'тут', 'завжди', 'ніколи', 'іноді', 'знову', 'просто',
    },
}


def load_dictionaries(langs: list[str] | None = None) -> dict[str, set[str]]:
    """
    Load word sets for the given languages (default: all built-in languages).
    Returns a dict of {lang: set_of_words}.
    """
    if langs is None:
        langs = list(_BUILTIN.keys())

    result: dict[str, set[str]] = {}
    for lang in langs:
        path = _DATA_DIR / f'{lang}_words.txt'
        if path.exists():
            with open(path, encoding='utf-8') as f:
                words = {line.strip().lower() for line in f if line.strip()}
            print(f'[{lang}] Loaded {len(words):,} words.')
            result[lang] = words
        else:
            print(f'[{lang}] Dictionary file not found, using built-in fallback.')
            result[lang] = _BUILTIN.get(lang, set()).copy()

    return result
