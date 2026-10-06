"""Local HTTP API and test page for EMA Lightning TTS."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.tts import TtsService

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_TEXT_CHARS = 4000
SampleRate = Literal[48000, 24000, 16000, 8000]

tts: TtsService | None = None


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_CHARS)
    speed: float = Field(1.0, ge=0.25, le=4.0)
    seed: int | None = Field(None, ge=0)
    sample_rate: SampleRate = 48000


@asynccontextmanager
async def lifespan(_: FastAPI):
    global tts
    tts = TtsService()
    yield
    tts = None


app = FastAPI(title="EMA Lightning TTS", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict:
    if tts is None:
        raise HTTPException(status_code=503, detail="Model is still loading")
    return {"status": "ok", "device": tts.device}


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
