"""TTS adapter (EMA Lightning): one model instance for the process lifetime."""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass

import numpy as np
from ema_lightning import EMA


@dataclass(frozen=True)
class SpeakResult:
    wav_bytes: bytes
    duration: float
    sample_rate: int
    seed: int


class TtsService:
    def __init__(self) -> None:
        self._tts = EMA()

    @property
    def device(self) -> str:
        return str(self._tts.device)

    def speak(
        self,
        text: str,
        *,
        speed: float = 1.0,
        seed: int | None = None,
        sample_rate: int = 48000,
    ) -> SpeakResult:
        speech = self._tts.say(text, speed=speed, seed=seed, sample_rate=sample_rate)
        return SpeakResult(
            wav_bytes=_to_wav_bytes(speech.audio, speech.sample_rate),
            duration=speech.duration,
            sample_rate=speech.sample_rate,
            seed=speech.seed,
        )


def _to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).round().astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())
    return buffer.getvalue()
