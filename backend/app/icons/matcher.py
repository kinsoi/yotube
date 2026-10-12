import re
import unicodedata
from collections.abc import Sequence

from app.icons.synonyms import RAW_TRANSLATIONS
from app.yoto.models import Icon

_WORD_RE = re.compile(r"\w+", re.UNICODE)

STOPWORDS = frozenset(
    {
        # English
        "the",
        "and",
        "for",
        "you",
        "with",
        "song",
        "songs",
        "kids",
        "children",
        "version",
        "remix",
        "remastered",
        "official",
        "video",
        "audio",
        "lyrics",
        "feat",
        "live",
        "edit",
        # French
        "les",
        "des",
        "une",
        "est",
        "dans",
        "pour",
        "sur",
        "avec",
        "aux",
        "qui",
        "mon",
        "ton",
        "son",
        "mes",
        "tes",
        "ses",
        "comptine",
        "comptines",
        # Russian
        "и",
        "в",
        "на",
        "не",
        "что",
        "как",
        "мой",
        "моя",
        "это",
        "для",
        "песенка",
    }
)


def normalize(text: str) -> str:
    """Casefold and strip combining accents (é → e, ё → е)."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


TRANSLATIONS = {normalize(word): english for word, english in RAW_TRANSLATIONS.items()}


def keywords(text: str) -> list[str]:
    """Meaningful words of a title, translated to English when known, without duplicates."""
    result: list[str] = []
    for raw in _WORD_RE.findall(text):
        word = normalize(raw)
        if len(word) < 3 or word.isdigit() or word in STOPWORDS:
            continue
        word = TRANSLATIONS.get(word, word)
        if word not in result:
            result.append(word)
    return result


def _score(words: Sequence[str], icon: Icon) -> int:
    title_words = {normalize(w) for w in _WORD_RE.findall(icon.title)}
    tags = {normalize(t) for t in icon.tags}
    score = 0
    for word in words:
        if word in title_words:
            score += 3
        elif word in tags:
            score += 2
        elif any(_prefix_match(word, candidate) for candidate in title_words | tags):
            score += 1
    return score


def _prefix_match(word: str, candidate: str) -> bool:
    if len(candidate) >= 3 and word.startswith(candidate):  # "trains" ~ "train"
        return True
    return len(word) >= 4 and candidate.startswith(word)  # "drag" ~ "dragon"


def rank(words: Sequence[str], icons: Sequence[Icon]) -> list[Icon]:
    scored = [
        (score, index, icon)
        for index, icon in enumerate(icons)
        if (score := _score(words, icon)) > 0
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [icon for _, _, icon in scored]


def best_match(words: Sequence[str], icons: Sequence[Icon]) -> Icon | None:
    ranked = rank(words, icons)
    return ranked[0] if ranked else None
