from app.icons.catalog import IconCatalog
from app.icons.picker import IconChoice, IconPicker
from app.yoto.models import Icon

LION = Icon("m-lion", "Lion", "https://i/lion.png", ("animal",))
CAT = Icon("m-cat", "Cat", "https://i/cat.png", ("animal", "pet"))
TRAIN = Icon("m-train", "Train", "https://i/train.png", ("vehicle",))


class FakeYoto:
    def __init__(self, icons: list[Icon] | None = None, fail: bool = False) -> None:
        self.icons = icons if icons is not None else [LION, CAT, TRAIN]
        self.fail = fail
        self.uploads: list[str] = []

    async def list_public_icons(self) -> list[Icon]:
        if self.fail:
            raise RuntimeError("Yoto down")
        return self.icons

    async def upload_icon(self, png: bytes, filename: str) -> Icon:
        self.uploads.append(filename)
        return Icon(f"up-{len(self.uploads)}", filename, f"https://i/{filename}")


class DictSettings:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value


class FakeSuggester:
    def __init__(self, words: list[str] | None = None, fail: bool = False) -> None:
        self.words = words or []
        self.fail = fail

    async def suggest(self, title: str, artist: str) -> list[str]:
        if self.fail:
            raise RuntimeError("API down")
        return self.words


def make(
    yoto: FakeYoto | None = None, suggester: FakeSuggester | None = None
) -> tuple[IconPicker, FakeYoto]:
    yoto = yoto or FakeYoto()
    return IconPicker(IconCatalog(yoto), yoto, DictSettings(), suggester), yoto


async def test_claude_keywords_win() -> None:
    picker, _ = make(suggester=FakeSuggester(["train", "vehicle"]))
    assert await picker.pick("Wheels on the bus", "", "orange") == IconChoice(
        "m-train", "https://i/train.png"
    )


async def test_falls_back_to_title_keywords_when_claude_fails() -> None:
    picker, _ = make(suggester=FakeSuggester(fail=True))
    assert await picker.pick("The Lion Sleeps Tonight", "", "orange") == IconChoice(
        "m-lion", "https://i/lion.png"
    )


async def test_falls_back_to_title_keywords_when_claude_has_no_match() -> None:
    picker, _ = make(suggester=FakeSuggester(["banana"]))
    choice = await picker.pick("Mon petit chat", "", "orange")
    assert choice is not None
    assert choice.media_id == "m-cat"


async def test_picker_matches_cyrillic_title() -> None:
    picker, _ = make()
    choice = await picker.pick("Кошка", "", "orange")
    assert choice is not None
    assert choice.media_id == "m-cat"


async def test_default_note_icon_is_uploaded_once_per_colour() -> None:
    picker, yoto = make()
    first = await picker.pick("Untitled melody", "", "blue")
    second = await picker.pick("Another tune", "", "blue")
    other = await picker.pick("Something", "", "green")
    assert first == second == IconChoice("up-1", "https://i/yotube-note-blue.png")
    assert other is not None
    assert other.media_id == "up-2"
    assert yoto.uploads == ["yotube-note-blue.png", "yotube-note-green.png"]


async def test_default_icon_used_when_catalog_unavailable() -> None:
    picker, _ = make(yoto=FakeYoto(fail=True))
    choice = await picker.pick("The Lion", "", "orange")
    assert choice is not None
    assert choice.media_id == "up-1"


async def test_returns_none_when_even_upload_fails() -> None:
    class BrokenYoto(FakeYoto):
        async def upload_icon(self, png: bytes, filename: str) -> Icon:
            raise RuntimeError("nope")

    picker, _ = make(yoto=BrokenYoto(icons=[]))
    assert await picker.pick("Nothing", "", "orange") is None
