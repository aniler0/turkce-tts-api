"""turkce-tts-api: ready-to-run Turkish TTS HTTP API (no UI)."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from app.chat import ChatService
from app.tts import TtsService

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MAX_TEXT_CHARS = 4000
MAX_HISTORY = 8
SampleRate = Literal[48000, 24000, 16000, 8000]

tts: TtsService | None = None
chat: ChatService | None = None


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_CHARS)
    speed: float = Field(1.0, ge=0.25, le=4.0)
    seed: int | None = Field(None, ge=0)
    sample_rate: SampleRate = 48000


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=MAX_TEXT_CHARS)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=MAX_HISTORY)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global tts, chat
    tts = TtsService()
    chat = ChatService.maybe_create()
    yield
    tts = None
    chat = None


app = FastAPI(title="turkce-tts-api", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Duration", "X-Seed", "X-Sample-Rate"],
)


@app.get("/")
async def root() -> dict:
    return {
        "service": "turkce-tts-api",
        "health": "/health",
        "speak": "POST /v1/speak",
        "chat": "POST /v1/chat" if chat is not None else None,
    }


@app.get("/health")
async def health() -> dict:
    if tts is None:
        raise HTTPException(status_code=503, detail="Model is still loading")
    return {
        "status": "ok",
        "device": tts.device,
        "chat": chat is not None,
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini") if chat else None,
    }


@app.post("/v1/speak")
async def speak(body: SpeakRequest) -> Response:
    if tts is None:
        raise HTTPException(status_code=503, detail="Model is still loading")

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text must not be empty")

    try:
        result = await asyncio.to_thread(
            tts.speak,
            text,
            speed=body.speed,
            seed=body.seed,
            sample_rate=body.sample_rate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(
        content=result.wav_bytes,
        media_type="audio/wav",
        headers={
            "X-Duration": f"{result.duration:.4f}",
            "X-Seed": str(result.seed),
            "X-Sample-Rate": str(result.sample_rate),
        },
    )


@app.post("/v1/chat")
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    if chat is None:
        raise HTTPException(
            status_code=503,
            detail="Chat disabled: set OPENAI_API_KEY to enable the LLM",
        )

    messages = [{"role": m.role, "content": m.content.strip()} for m in body.messages]
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")

    async def events():
        try:
            async for piece in chat.stream_reply(messages):
                yield f"data: {json.dumps({'type': 'token', 'text': piece}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:  # noqa: BLE001 - surface to client as SSE error
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
