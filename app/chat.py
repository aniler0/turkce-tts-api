"""OpenAI chat streaming for short Turkish voice replies."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Literal, Self

from openai import AsyncOpenAI

SYSTEM_PROMPT = (
    "Sen samimi, kısa ve net konuşan bir Türkçe sesli asistanısın. "
    "Cevapların 1–3 cümle olsun. Gereksiz giriş veya madde listesi yazma. "
    "Konuşulur gibi yaz; seslendirileceğini unutma."
)

Role = Literal["user", "assistant"]


def openai_api_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or key in {"sk-proj-...", "your-key-here", "changeme"}:
        return None
    return key


class ChatService:
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        self.max_tokens = int(os.environ.get("OPENAI_MAX_TOKENS", "160"))

    @classmethod
    def maybe_create(cls) -> Self | None:
        key = openai_api_key()
        if not key:
            return None
        return cls(key)

    async def stream_reply(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            max_tokens=self.max_tokens,
            temperature=0.7,
            stream=True,
        )
        async for event in stream:
            delta = event.choices[0].delta.content if event.choices else None
            if delta:
                yield delta
