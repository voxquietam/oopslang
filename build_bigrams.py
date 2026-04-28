"""
Build bigram frequency tables from text corpora and save to data/bigrams.json.
Run once: python build_bigrams.py

Sources: Wikipedia API (plain text extracts, guaranteed UTF-8).
"""

import json
import re
import urllib.request
import urllib.parse
from collections import Counter
from pathlib import Path

# Wikipedia article titles per language
WIKI_SOURCES = {
    'en': ('en', ['Python_(programming_language)', 'United_States', 'Science',
                  'History', 'Earth', 'Language', 'Music', 'Literature', 'Technology']),
    'ru': ('ru', ['Россия', 'История', 'Наука', 'Язык', 'Земля', 'Музыка',
                  'Литература', 'Технология', 'Философия', 'Математика']),
    'uk': ('uk', ['Україна', 'Історія', 'Наука', 'Мова', 'Земля', 'Музика',
                  'Література', 'Технологія', 'Філософія', 'Математика']),
}

# Characters belonging to each language (for filtering noise)
LANG_CHARS = {
    'en': set('abcdefghijklmnopqrstuvwxyz'),
    'ru': set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),
    'uk': set('абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'),
}

DATA_DIR = Path(__file__).parent / 'data'


def fetch_wikipedia_batch(lang_code: str, titles: list[str]) -> str:
    """Fetch all titles in a single API request."""
    params = urllib.parse.urlencode({
        'action': 'query',
        'prop': 'extracts',
        'explaintext': '1',
        'format': 'json',
        'titles': '|'.join(titles),
    })
    url = f'https://{lang_code}.wikipedia.org/w/api.php?{params}'
    print(f'  Fetching {len(titles)} articles in one request...', end=' ', flush=True)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'oopslang-bigram-builder/1.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode('utf-8'))
        pages = data['query']['pages']
        combined = ' '.join(p.get('extract', '') for p in pages.values())
        print(f'ok ({len(combined):,} chars)')
        return combined
    except Exception as e:
        print(f'FAILED: {e}')
        return ''


def compute_bigrams(text: str, lang: str) -> dict[str, float]:
    valid = LANG_CHARS[lang]
    text = text.lower()
    # Keep only valid chars, split on anything else
    tokens = re.findall(f'[{"".join(valid)}]+', text)

    counts: Counter = Counter()
    total = 0
    for token in tokens:
        for i in range(len(token) - 1):
            pair = token[i:i + 2]
            counts[pair] += 1
            total += 1

    if total == 0:
        return {}

    # Convert to log-probabilities, keep top 500
    top = counts.most_common(500)
    return {pair: count / total for pair, count in top}


def build():
    DATA_DIR.mkdir(exist_ok=True)
    result: dict[str, dict[str, float]] = {}

    for lang, (wiki_code, titles) in WIKI_SOURCES.items():
        print(f'\n[{lang}]')
        combined = fetch_wikipedia_batch(wiki_code, titles)

        if not combined:
            print(f'  No text for {lang}, skipping.')
            continue

        bigrams = compute_bigrams(combined, lang)
        print(f'  Computed {len(bigrams)} bigrams from {len(combined):,} chars')
        result[lang] = bigrams

    out = DATA_DIR / 'bigrams.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'\nSaved to {out}')


if __name__ == '__main__':
    build()
