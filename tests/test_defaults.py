from app.core.defaults import (
    ASR_CONTEXT_WINDOW_SECONDS,
    EMBEDDING_DIMENSION,
    FRAME_TOP_K,
    LOW_CONFIDENCE_THRESHOLD,
    SCENE_TOP_K,
)


def test_defaults_are_positive() -> None:
    assert EMBEDDING_DIMENSION > 0
    assert ASR_CONTEXT_WINDOW_SECONDS > 0
    assert SCENE_TOP_K > 0
    assert FRAME_TOP_K > 0
    assert 0 < LOW_CONFIDENCE_THRESHOLD < 1
