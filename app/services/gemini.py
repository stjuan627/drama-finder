from __future__ import annotations

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

        parts: list[Any] = [text]
        for image_path in image_paths:
            mime_type = (
                "image/jpeg"
                if image_path.suffix.lower() in {".jpg", ".jpeg"}
                else "image/png"
            )
            parts.append(types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type))

        response = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=parts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dimension,
            ),
        )
        return list(response.embeddings[0].values)


class SceneMergeService:
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
            return [
                {
                    "scene_index": shot["shot_index"],
                    "start": shot["start"],
                    "end": shot["end"],
                    "summary": "",
                    "shot_indexes": [shot["shot_index"]],
                }
                for shot in shots
            ]

        prompt = {
            "instruction": (
                "将镜头列表合并为语义 scene，输出 JSON 数组。"
                "每个元素必须包含 scene_index、start、end、summary、shot_indexes。"
            ),
            "shots": shots,
            "asr_segments": asr_segments,
        }
        response = client.models.generate_content(
            model=settings.gemini_scene_model,
            contents=str(prompt),
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return response.parsed
