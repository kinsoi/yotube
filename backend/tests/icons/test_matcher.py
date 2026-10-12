from app.icons.matcher import best_match, keywords, normalize, rank
from app.yoto.models import Icon

LION = Icon("m-lion", "Lion", "https://i/lion.png", ("animal", "safari"))
CAT = Icon("m-cat", "Cat", "https://i/cat.png", ("animal", "pet"))
ELEPHANT = Icon("m-elephant", "Elephant", "https://i/elephant.png", ("animal",))
STAR = Icon("m-star", "Shooting star", "https://i/star.png", ("night", "space"))
TRAIN = Icon("m-train", "Steam train", "https://i/train.png", ("vehicle",))
ICONS = [LION, CAT, ELEPHANT, STAR, TRAIN]


def test_normalize_strips_accents_and_case() -> None:
    assert normalize("Éléphant") == "elephant"
    assert normalize("КОШКА") == "кошка"


def test_keywords_drop_stopwords_and_short_words() -> None:
    assert keywords("The Lion Sleeps Tonight") == ["lion", "sleeps", "tonight"]


def test_keywords_translate_french_and_russian() -> None:
    assert keywords("Le petit Éléphant") == ["petit", "elephant"]
    assert keywords("Кошка и котята") == ["cat", "котята"]


def test_best_match_prefers_title_over_tag() -> None:
    assert best_match(["lion"], ICONS) == LION
    assert best_match(["animal", "cat"], ICONS) == CAT


def test_best_match_handles_plurals_by_prefix() -> None:
    assert best_match(["trains"], ICONS) == TRAIN
    assert best_match(["stars"], ICONS) == STAR


def test_best_match_returns_none_without_signal() -> None:
    assert best_match(["banana"], ICONS) is None
    assert best_match([], ICONS) is None


def test_rank_orders_by_score() -> None:
    assert rank(["night", "star"], ICONS)[0] == STAR
    assert rank(["animal"], ICONS) == [LION, CAT, ELEPHANT]
