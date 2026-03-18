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
            parts.append("empty frame")

        response = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=parts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dimension,
            ),
        )
        return list(response.embeddings[0].values)

    def embed_frame_document(self, image_path: Path, context_text: str) -> list[float]:
        return self.embed_multimodal(
            text=context_text,
            image_paths=[image_path],
            task_type="RETRIEVAL_DOCUMENT",
        )
