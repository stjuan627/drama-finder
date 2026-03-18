from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings

settings = get_settings()

_SENSEVOICE_TAG_RE = re.compile(r"<\|[^|]+?\|>")


class ASRService:
    def __init__(self) -> None:
        self._model: Any | None = None

    def transcribe(self, audio_path: Path) -> list[dict[str, Any]]:
        model = self._load_model()
        raw_result = self._run_inference(model, audio_path)
        return self._normalize_segments(raw_result)

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        try:
            from funasr_onnx import SenseVoiceSmall
        except ImportError as exc:
            raise RuntimeError(
                "SenseVoice ONNX runtime is not installed. "
                "Install the 'pipeline' extra to enable ASR."
            ) from exc

        model_source = settings.asr_model_dir.strip() or settings.asr_model_name
        init_kwargs = self._build_init_kwargs(SenseVoiceSmall)
        self._model = SenseVoiceSmall(model_source, **init_kwargs)
        return self._model

    @staticmethod
    def _build_init_kwargs(model_cls: Any) -> dict[str, Any]:
        try:
            parameters = inspect.signature(model_cls).parameters
        except (TypeError, ValueError):
            parameters = {}

        kwargs: dict[str, Any] = {}
        if "device" in parameters:
            kwargs["device"] = settings.asr_device
        if "quantize" in parameters:
            kwargs["quantize"] = settings.asr_compute_type.lower() in {"int8", "int8_float16"}
        return kwargs

    @staticmethod
    def _run_inference(model: Any, audio_path: Path) -> Any:
        target = str(audio_path)
        if hasattr(model, "transcribe"):
            return model.transcribe(target)
        if hasattr(model, "inference"):
            return model.inference(target)
        if callable(model):
            return model(target)
        raise RuntimeError("SenseVoice model has no usable inference entrypoint")

    def _normalize_segments(self, raw_result: Any) -> list[dict[str, Any]]:
        sentence_entries = self._extract_sentence_entries(raw_result)
        if sentence_entries:
            normalized = [self._convert_sentence_entry(entry) for entry in sentence_entries]
            return [segment for segment in normalized if segment["text"]]

        plain_text = self._extract_plain_text(raw_result)
        if not plain_text:
            return []
        return [{"start": 0.0, "end": 0.0, "text": plain_text}]

    def _extract_sentence_entries(self, raw_result: Any) -> list[dict[str, Any]]:
        if isinstance(raw_result, dict):
            if isinstance(raw_result.get("sentence_info"), list):
                return [item for item in raw_result["sentence_info"] if isinstance(item, dict)]
            if isinstance(raw_result.get("sentences"), list):
                return [item for item in raw_result["sentences"] if isinstance(item, dict)]
            if isinstance(raw_result.get("segments"), list):
                return [item for item in raw_result["segments"] if isinstance(item, dict)]
            return []

        if isinstance(raw_result, list):
            entries: list[dict[str, Any]] = []
            for item in raw_result:
                entries.extend(self._extract_sentence_entries(item))
            return entries

        return []

    def _extract_plain_text(self, raw_result: Any) -> str:
        if isinstance(raw_result, str):
            return self._clean_text(raw_result)
        if isinstance(raw_result, dict):
            for key in ("text", "result"):
                value = raw_result.get(key)
                if isinstance(value, str):
                    return self._clean_text(value)
        if isinstance(raw_result, list):
            chunks = [self._extract_plain_text(item) for item in raw_result]
            merged = " ".join(chunk for chunk in chunks if chunk)
            return self._clean_text(merged)
        return ""

    def _convert_sentence_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        start_value = (
            entry.get("start")
            if entry.get("start") is not None
            else entry.get("start_ms", entry.get("start_time", 0.0))
        )
        end_value = (
            entry.get("end")
            if entry.get("end") is not None
            else entry.get("end_ms", entry.get("end_time", start_value))
        )
        text_value = entry.get("text") or entry.get("sentence") or entry.get("result") or ""

        start_ts = self._coerce_timestamp(start_value)
        end_ts = self._coerce_timestamp(end_value)
        if end_ts < start_ts:
            end_ts = start_ts

        return {
            "start": start_ts,
            "end": end_ts,
            "text": self._clean_text(str(text_value)),
        }

    @staticmethod
    def _coerce_timestamp(value: Any) -> float:
        try:
            raw = float(value)
        except (TypeError, ValueError):
            return 0.0
        return raw / 1000.0 if raw > 1000.0 else raw

    @staticmethod
    def _clean_text(text: str) -> str:
        stripped = _SENSEVOICE_TAG_RE.sub("", text).replace("\n", " ").strip()
        return " ".join(stripped.split())
