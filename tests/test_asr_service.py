from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from app.services.asr import ASRService


def test_merge_vad_segments_merges_close_ranges_and_splits_long_ranges() -> None:
    merged = ASRService._merge_vad_segments(
        segments=[(0, 1000), (1200, 2500), (4000, 39000)],
        gap_ms=300,
        max_segment_ms=30000,
    )

    assert merged == [(0, 2500), (4000, 34000), (34000, 39000)]


def test_prepare_vad_model_dir_converts_vad_yaml_layout(tmp_path: Path) -> None:
    model_dir = tmp_path / "vad-model"
    model_dir.mkdir()
    (model_dir / "model.onnx").write_bytes(b"onnx")
    (model_dir / "model_quant.onnx").write_bytes(b"quant")
    (model_dir / "vad.mvn").write_bytes(b"mvn")
    (model_dir / "vad.yaml").write_text(
        yaml.safe_dump(
            {
                "frontend_conf": {"fs": 16000},
                "encoder_conf": {"fsmn_layers": 1, "proj_dim": 2, "lorder": 3},
                "vad_post_conf": {"max_end_silence_time": 800},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    compat_dir = ASRService()._prepare_vad_model_dir(model_dir)
    compat_config = yaml.safe_load((compat_dir / "config.yaml").read_text(encoding="utf-8"))

    assert compat_config["model_conf"]["max_end_silence_time"] == 800
    assert (compat_dir / "am.mvn").read_bytes() == b"mvn"
    assert (compat_dir / "model_quant.onnx").exists()


def test_transcribe_builds_timed_segments_from_streaming_vad(monkeypatch) -> None:
    service = ASRService()

    monkeypatch.setattr(service, "_load_model", lambda: object())
    monkeypatch.setattr(service, "_load_vad_model", lambda: object())
    monkeypatch.setattr(
        service,
        "_stream_vad_segments",
        lambda _audio_path, _vad_model: [(1000, 2500), (4000, 5200)],
    )
    monkeypatch.setattr(
        service,
        "_read_wave_segment",
        lambda _audio_path, start_ms, end_ms: np.array([start_ms, end_ms], dtype=np.float32),
    )

    seen_waveforms: list[list[float]] = []

    def fake_transcribe_waveform(_model: object, waveform: np.ndarray) -> str:
        seen_waveforms.append(waveform.tolist())
        return "片段文本"

    monkeypatch.setattr(service, "_transcribe_waveform", fake_transcribe_waveform)

    result = service.transcribe(Path("/tmp/fake.wav"))

    assert seen_waveforms == [[1000.0, 2500.0], [4000.0, 5200.0]]
    assert result == [
        {"start": 1.0, "end": 2.5, "text": "片段文本"},
        {"start": 4.0, "end": 5.2, "text": "片段文本"},
    ]
