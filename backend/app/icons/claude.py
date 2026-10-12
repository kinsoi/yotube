import json
from typing import Any

SYSTEM_PROMPT = (
    "You help pick a 16x16 pixel-art icon for a song on a children's audio player. "
    "Given a song title and artist, list up to 5 concrete English nouns a young child "
    "would associate with the song: animals, objects, vehicles, food, weather, places or "
    "characters. Prefer things that can be drawn in 16x16 pixels. Use lowercase singular nouns, "
    "most relevant first."
)

KEYWORDS_SCHEMA = {
    "type": "object",
    "properties": {"keywords": {"type": "array", "items": {"type": "string"}}},
    "required": ["keywords"],
    "additionalProperties": False,
}

MAX_KEYWORDS = 5


class ClaudeKeywordSuggester:
    """Asks Claude for icon keywords describing a song."""

    def __init__(self, client: Any, model: str) -> None:
        self._client = client  # anthropic.AsyncAnthropic
        self._model = model

    async def suggest(self, title: str, artist: str) -> list[str]:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Title: {title}\nArtist: {artist or 'unknown'}"}
            ],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": KEYWORDS_SCHEMA},
            },
        )
        if response.stop_reason == "refusal":
            return []
        text = next((block.text for block in response.content if block.type == "text"), "")
        words = json.loads(text).get("keywords", [])
        return [str(word).strip().lower() for word in words if str(word).strip()][:MAX_KEYWORDS]
