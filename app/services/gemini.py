from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Sequence, cast

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

    @staticmethod
    def _guess_image_mime_type(image_path: Path) -> str:
        mime_type, _ = mimetypes.guess_type(image_path.name)
        if mime_type and mime_type.startswith("image/"):
            return mime_type
        return "image/jpeg"

    @staticmethod
    def _extract_embedding_values(response: Any) -> list[float]:
        embeddings = getattr(response, "embeddings", None)
        if not embeddings:
            raise RuntimeError("Gemini embedding response is empty")
        first_embedding = embeddings[0]
        values = getattr(first_embedding, "values", None)
        if values is None:
            raise RuntimeError("Gemini embedding response has no values")
        return list(cast(Sequence[float], values))

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
        return self._extract_embedding_values(response)

    def embed_image(self, image_path: Path, task_type: str = "RETRIEVAL_QUERY") -> list[float]:
        client = self._factory.build()
        from google.genai import types

        image_part = types.Part.from_bytes(
            data=image_path.read_bytes(),
            mime_type=self._guess_image_mime_type(image_path),
        )
        response = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=[image_part],
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dimension,
            ),
        )
        return self._extract_embedding_values(response)

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
            mime_type = self._guess_image_mime_type(image_path)
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
        return self._extract_embedding_values(response)

    def embed_frame_document(self, image_path: Path, context_text: str) -> list[float]:
        return self.embed_image(image_path=image_path, task_type="RETRIEVAL_DOCUMENT")
