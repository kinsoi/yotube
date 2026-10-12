from types import SimpleNamespace
from typing import Any

from app.icons.claude import ClaudeKeywordSuggester


class FakeMessages:
    def __init__(self, text: str, stop_reason: str = "end_turn") -> None:
        self.text = text
        self.stop_reason = stop_reason
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(
            stop_reason=self.stop_reason,
            content=[SimpleNamespace(type="text", text=self.text)],
        )


def make(text: str, stop_reason: str = "end_turn") -> tuple[ClaudeKeywordSuggester, FakeMessages]:
    messages = FakeMessages(text, stop_reason)
    return ClaudeKeywordSuggester(SimpleNamespace(messages=messages), "claude-haiku-5-5"), messages


async def test_suggest_returns_lowercase_keywords_and_uses_structured_output() -> None:
    suggester, messages = make('{"keywords": ["Lion", "jungle", "night"]}')
    assert await suggester.suggest("The Lion Sleeps Tonight", "The Tokens") == [
        "lion",
        "jungle",
        "night",
    ]
    assert messages.kwargs["model"] == "claude-haiku-5-5"
    assert messages.kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "The Lion Sleeps Tonight" in messages.kwargs["messages"][0]["content"]


async def test_suggest_caps_at_five_keywords() -> None:
    suggester, _ = make('{"keywords": ["a1", "b2", "c3", "d4", "e5", "f6"]}')
    assert len(await suggester.suggest("x", "y")) == 5


async def test_refusal_returns_no_keywords() -> None:
    suggester, _ = make("", stop_reason="refusal")
    assert await suggester.suggest("x", "y") == []
