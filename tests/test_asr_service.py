from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import yaml

from app.services import asr as asr_module
from app.services.asr import ASRService


def test_split_segment_windows_splits_long_ranges() -> None:
    windows = ASRService._split_segment_windows(
        start_ms=4000,
        end_ms=39000,
        max_segment_ms=30000,
    )

    assert windows == [(4000, 34000), (34000, 39000)]


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


def test_transcribe_streams_audio_and_builds_timed_segments(monkeypatch) -> None:
    service = ASRService()
    monkeypatch.setattr(asr_module.settings, "asr_backend", "python")

    monkeypatch.setattr(service, "_load_model", lambda: object())
    monkeypatch.setattr(service, "_load_vad_model", lambda: object())

    expected = [{"start": 1.0, "end": 2.5, "text": "片段文本"}]
    monkeypatch.setattr(service, "_stream_transcribe", lambda *_args: expected)

    result = service.transcribe(Path("/tmp/fake.wav"))

    assert result == expected


def test_transcribe_uses_node_backend(monkeypatch, tmp_path: Path) -> None:
    service = ASRService()
    monkeypatch.setattr(asr_module.settings, "asr_backend", "node")
    monkeypatch.setattr(asr_module.settings, "asr_cpu_cores", 2)
    monkeypatch.setattr(asr_module.settings, "asr_node_project_dir", tmp_path / "coli")
    monkeypatch.setattr(
        asr_module.settings,
        "asr_node_cli_path",
        Path("scripts/node_stream_asr.mjs"),
    )
    monkeypatch.setattr(asr_module.settings, "asr_node_model_dir", None)
    monkeypatch.setattr(asr_module.settings, "asr_node_vad_model_path", None)

    completed = SimpleNamespace(stdout='[{"start":1.0,"end":2.5,"text":" 片段文本 "}]')
    seen: dict[str, object] = {}

    def fake_run(command: list[str], check: bool, capture_output: bool, text: bool):
        seen["command"] = command
        seen["check"] = check
        seen["capture_output"] = capture_output
        seen["text"] = text
        return completed

    monkeypatch.setattr(asr_module.subprocess, "run", fake_run)

    result = service.transcribe(Path("/tmp/fake.wav"))

    assert result == [{"start": 1.0, "end": 2.5, "text": "片段文本"}]
    assert seen["check"] is True
    assert seen["capture_output"] is True
    assert seen["text"] is True
    expected_cli = str((Path.cwd() / "scripts/node_stream_asr.mjs").resolve())
    assert seen["command"][:2] == ["node", expected_cli]


def test_consume_stream_segment_merges_close_ranges() -> None:
    pending, flushed = ASRService()._consume_stream_segment(
        pending_segment=(1000, 2000),
        incoming_segment=(2200, 2800),
        buffer=np.array([], dtype=np.float32),
        buffer_start_ms=0,
        sample_rate=16000,
        model=object(),
    )

    assert pending == (1000, 2800)
    assert flushed == []


def test_slice_and_trim_audio_buffer() -> None:
    sample_rate = 10
    buffer = np.arange(100, dtype=np.float32)

    sliced = ASRService._slice_buffer_waveform(
        buffer=buffer,
        buffer_start_ms=1000,
        start_ms=2000,
        end_ms=4000,
        sample_rate=sample_rate,
    )
    trimmed_buffer, trimmed_start = ASRService._trim_audio_buffer(
        buffer=buffer,
        buffer_start_ms=1000,
        keep_from_ms=3000,
        sample_rate=sample_rate,
    )

    assert sliced.tolist() == list(range(10, 30))
    assert trimmed_start == 3000
    assert trimmed_buffer.tolist() == list(range(20, 100))
