from __future__ import annotations

from pathlib import Path
from typing import Any


class ASRService:
    def transcribe(self, audio_path: Path) -> list[dict[str, Any]]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Install the 'pipeline' extra to enable ASR."
            ) from exc

        model = WhisperModel("large-v3", device="auto", compute_type="int8")
        segments, _ = model.transcribe(str(audio_path), language="zh")

        output: list[dict[str, Any]] = []
        for segment in segments:
            output.append(
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": segment.text.strip(),
                }
            )
        return output
