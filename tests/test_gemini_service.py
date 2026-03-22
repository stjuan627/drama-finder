from pathlib import Path

from app.services.gemini import GeminiEmbeddingService


def test_guess_image_mime_type_uses_real_suffixes() -> None:
    service = GeminiEmbeddingService()

    assert service._guess_image_mime_type(Path("frame.jpg")) == "image/jpeg"
    assert service._guess_image_mime_type(Path("frame.jpeg")) == "image/jpeg"
    assert service._guess_image_mime_type(Path("frame.png")) == "image/png"
    assert service._guess_image_mime_type(Path("frame.webp")) == "image/webp"


def test_guess_image_mime_type_falls_back_to_jpeg_for_unknown_suffix() -> None:
    service = GeminiEmbeddingService()

    assert service._guess_image_mime_type(Path("frame.unknownext")) == "image/jpeg"
