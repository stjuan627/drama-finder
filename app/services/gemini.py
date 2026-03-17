from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings

settings = get_settings()


class GeminiConfigurationError(RuntimeError):
    """Raised when Gemini is required but missing configuration."""


class GeminiClientFactory:
    def build(self):
        if not settings.gemini_api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY is not configured")

        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai is not installed") from exc

        return genai.Client(api_key=settings.gemini_api_key)


class GeminiEmbeddingService:
    def __init__(self) -> None:
        self._factory = GeminiClientFactory()

    def embed_text(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        client = self._factory.build()
        from google.genai import types

        response = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dimension,
            ),
        )
        return list(response.embeddings[0].values)

    def embed_image(self, image_path: Path, task_type: str = "RETRIEVAL_QUERY") -> list[float]:
        client = self._factory.build()
        from google.genai import types

        image_part = types.Part.from_bytes(data=image_path.read_bytes(), mime_type="image/jpeg")
        response = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=[image_part],
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dimension,
            ),
        )
        return list(response.embeddings[0].values)

    def embed_multimodal(
        self, text: str, image_paths: list[Path], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[float]:
        client = self._factory.build()
        from google.genai import types

        parts: list[Any] = []
        cleaned_text = text.strip()
        if cleaned_text:
            parts.append(cleaned_text)
        for image_path in image_paths:
            mime_type = (
                "image/jpeg"
                if image_path.suffix.lower() in {".jpg", ".jpeg"}
                else "image/png"
            )
            parts.append(types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type))

        if not parts:
            parts.append("empty scene")

        response = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=parts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dimension,
            ),
        )
        return list(response.embeddings[0].values)


class SegmentBuildService:
    def __init__(self) -> None:
        self._factory = GeminiClientFactory()

    def merge(
        self,
        shots: list[dict[str, Any]],
        asr_segments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not shots:
            return []

        try:
            client = self._factory.build()
            from google.genai import types
        except Exception:
            return self._fallback_segments(shots, asr_segments)

        prompt = {
            "instruction": (
                "将镜头列表合并为语义连续、时长可读的 segment，输出 JSON 数组。"
                "每个元素必须包含 segment_index、start、end、summary、shot_indexes。"
                f"优先让每个 segment 时长落在 {settings.segment_target_min_seconds}"
                f" 到 {settings.segment_target_max_seconds} 秒之间。"
            ),
            "shots": shots,
            "asr_segments": asr_segments,
        }
        response = client.models.generate_content(
            model=settings.gemini_scene_model,
            contents=str(prompt),
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        parsed = getattr(response, "parsed", None)
        if not isinstance(parsed, list) or not parsed:
            return self._fallback_segments(shots, asr_segments)
        normalized = self._normalize_segments(parsed)
        return normalized or self._fallback_segments(shots, asr_segments)

    @staticmethod
    def _normalize_segments(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for index, segment in enumerate(payload):
            shot_indexes = segment.get("shot_indexes", [])
            if not shot_indexes:
                continue
            normalized.append(
                {
                    "segment_index": int(segment.get("segment_index", index)),
                    "start": float(segment["start"]),
                    "end": float(segment["end"]),
                    "summary": str(segment.get("summary", "")).strip(),
                    "shot_indexes": [int(item) for item in shot_indexes],
                }
            )
        return normalized

    @staticmethod
    def _text_overlaps(asr_segments: list[dict[str, Any]], start_ts: float, end_ts: float) -> str:
        fragments: list[str] = []
        for segment in asr_segments:
            if segment["end"] < start_ts or segment["start"] > end_ts:
                continue
            text = str(segment.get("text", "")).strip()
            if text:
                fragments.append(text)
        return " ".join(fragments)

    def _fallback_segments(
        self,
        shots: list[dict[str, Any]],
        asr_segments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        min_seconds = float(settings.segment_target_min_seconds)
        max_seconds = float(settings.segment_target_max_seconds)
        segments: list[dict[str, Any]] = []
        current: list[dict[str, Any]] = []

        def flush() -> None:
            nonlocal current
            if not current:
                return
            start_ts = float(current[0]["start"])
            end_ts = float(current[-1]["end"])
            summary_text = self._text_overlaps(asr_segments, start_ts, end_ts)
            summary_text = re.sub(r"\s+", " ", summary_text).strip()
            segments.append(
                {
                    "segment_index": len(segments),
                    "start": start_ts,
                    "end": end_ts,
                    "summary": summary_text[:200],
                    "shot_indexes": [int(shot["shot_index"]) for shot in current],
                }
            )
            current = []

        for shot in shots:
            candidate = current + [shot]
            duration = float(candidate[-1]["end"]) - float(candidate[0]["start"])
            current = candidate

            if duration < min_seconds:
                continue

            asr_text = self._text_overlaps(asr_segments, current[0]["start"], current[-1]["end"])
            sentence_closed = bool(re.search(r"[。！？!?]\s*$", asr_text.strip()))
            if duration >= max_seconds or sentence_closed:
                flush()

        flush()
        return segments


SceneMergeService = SegmentBuildService
