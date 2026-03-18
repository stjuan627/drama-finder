from __future__ import annotations

import hashlib
import inspect
import json
import re
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from app.core.config import get_settings

settings = get_settings()

_SENSEVOICE_TAG_RE = re.compile(r"<\|[^|]+?\|>")


class ASRService:
    def __init__(self) -> None:
        self._model: Any | None = None
        self._vad_model: Any | None = None

    def transcribe(self, audio_path: Path) -> list[dict[str, Any]]:
        if settings.asr_backend.lower() == "node":
            return self._transcribe_with_node(audio_path)
        return self._transcribe_with_python(audio_path)

    def _transcribe_with_node(self, audio_path: Path) -> list[dict[str, Any]]:
        script_path = self._resolve_node_cli_path()
        project_dir = settings.asr_node_project_dir.expanduser().resolve()
        command = [
            "node",
            str(script_path),
            "--input",
            str(audio_path),
            "--project-dir",
            str(project_dir),
            "--cores",
            str(settings.asr_cpu_cores),
        ]
        if settings.asr_node_model_dir is not None:
            command.extend(["--model-dir", str(settings.asr_node_model_dir.expanduser())])
        if settings.asr_node_vad_model_path is not None:
            command.extend(
                ["--vad-model", str(settings.asr_node_vad_model_path.expanduser())]
            )

        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        if not isinstance(payload, list):
            raise RuntimeError("node ASR CLI did not return a list payload")
        return [
            {
                "start": round(float(item["start"]), 3),
                "end": round(float(item["end"]), 3),
                "text": self._clean_text(str(item["text"])),
            }
            for item in payload
            if isinstance(item, dict) and str(item.get("text", "")).strip()
        ]

    @staticmethod
    def _resolve_node_cli_path() -> Path:
        cli_path = settings.asr_node_cli_path.expanduser()
        if cli_path.is_absolute():
            return cli_path.resolve()
        return (Path.cwd() / cli_path).resolve()

    def _transcribe_with_python(self, audio_path: Path) -> list[dict[str, Any]]:
        model = self._load_model()
        vad_model = self._load_vad_model()
        return self._stream_transcribe(audio_path, vad_model, model)

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

        model_source = self._resolve_model_source(
            settings.asr_model_dir.strip() or settings.asr_model_name
        )
        init_kwargs = self._build_init_kwargs(SenseVoiceSmall)
        self._model = SenseVoiceSmall(model_source, **init_kwargs)
        return self._model

    def _load_vad_model(self) -> Any:
        if self._vad_model is not None:
            return self._vad_model

        try:
            from funasr_onnx import Fsmn_vad_online
        except ImportError as exc:
            raise RuntimeError(
                "FunASR VAD ONNX runtime is not installed. "
                "Install the 'pipeline' extra to enable streaming ASR."
            ) from exc

        model_source = settings.asr_vad_model_dir.strip() or settings.asr_vad_model_name
        resolved_source = self._resolve_model_source(model_source)
        compat_source = self._prepare_vad_model_dir(Path(resolved_source))
        init_kwargs = self._build_init_kwargs(Fsmn_vad_online)
        self._vad_model = Fsmn_vad_online(str(compat_source), **init_kwargs)
        return self._vad_model

    def _resolve_model_source(self, model_source: str) -> str:
        path = Path(model_source).expanduser()
        if path.exists():
            return str(path.resolve())

        if "/" not in model_source:
            return model_source

        try:
            from huggingface_hub import snapshot_download
        except ImportError:
            return model_source

        try:
            return snapshot_download(repo_id=model_source)
        except Exception:
            return model_source

    def _prepare_vad_model_dir(self, model_dir: Path) -> Path:
        if (model_dir / "config.yaml").exists() and (model_dir / "am.mvn").exists():
            return model_dir

        vad_yaml = model_dir / "vad.yaml"
        vad_mvn = model_dir / "vad.mvn"
        if not vad_yaml.exists() or not vad_mvn.exists():
            return model_dir

        digest = hashlib.sha1(str(model_dir).encode("utf-8")).hexdigest()[:12]
        compat_dir = Path(tempfile.gettempdir()) / "drama-finder-vad" / digest
        compat_dir.mkdir(parents=True, exist_ok=True)

        config = yaml.safe_load(vad_yaml.read_text(encoding="utf-8"))
        if "model_conf" not in config and "vad_post_conf" in config:
            config["model_conf"] = config.pop("vad_post_conf")
        (compat_dir / "config.yaml").write_text(
            yaml.safe_dump(config, sort_keys=False),
            encoding="utf-8",
        )
        (compat_dir / "am.mvn").write_bytes(vad_mvn.read_bytes())

        for filename in ("model.onnx", "model_quant.onnx"):
            source = model_dir / filename
            if source.exists():
                target = compat_dir / filename
                if not target.exists():
                    target.symlink_to(source)
        return compat_dir

    @staticmethod
    def _build_init_kwargs(model_cls: Any) -> dict[str, Any]:
        try:
            parameters = inspect.signature(model_cls).parameters
        except (TypeError, ValueError):
            parameters = {}

        kwargs: dict[str, Any] = {}
        if "device" in parameters:
            kwargs["device"] = settings.asr_device
        if "device_id" in parameters:
            kwargs["device_id"] = ASRService._resolve_device_id(settings.asr_device)
        if "intra_op_num_threads" in parameters:
            kwargs["intra_op_num_threads"] = settings.asr_cpu_cores
        if "quantize" in parameters:
            kwargs["quantize"] = settings.asr_compute_type.lower() in {"int8", "int8_float16"}
        return kwargs

    @staticmethod
    def _resolve_device_id(device: str) -> int | str:
        normalized = device.strip().lower()
        if normalized in {"", "cpu", "auto", "-1"}:
            return "-1"
        if normalized.startswith("cuda:"):
            suffix = normalized.split(":", 1)[1]
            return int(suffix) if suffix.isdigit() else suffix
        return int(normalized) if normalized.isdigit() else normalized

    def _stream_transcribe(
        self,
        audio_path: Path,
        vad_model: Any,
        model: Any,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        param_dict: dict[str, Any] = {"in_cache": [], "is_final": False}
        emitted_segments: set[tuple[int, int]] = set()
        pending_segment: tuple[int, int] | None = None
        buffer = np.array([], dtype=np.float32)
        buffer_start_ms = 0
        sample_rate = 16000

        with wave.open(str(audio_path), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            chunk_frames = max(
                1,
                int(sample_rate * settings.asr_stream_chunk_seconds),
            )
            while True:
                frames = wav_file.readframes(chunk_frames)
                if not frames:
                    break

                waveform = self._pcm16_bytes_to_waveform(
                    frames=frames,
                    channels=wav_file.getnchannels(),
                )
                if waveform.size == 0:
                    continue

                buffer = np.concatenate((buffer, waveform))
                param_dict["is_final"] = wav_file.tell() >= wav_file.getnframes()
                vad_segments = self._flatten_vad_segments(
                    vad_model(waveform, param_dict=param_dict)
                )
                for segment in vad_segments:
                    if segment in emitted_segments:
                        continue
                    emitted_segments.add(segment)
                    pending_segment, flushed_results = self._consume_stream_segment(
                        pending_segment=pending_segment,
                        incoming_segment=segment,
                        buffer=buffer,
                        buffer_start_ms=buffer_start_ms,
                        sample_rate=sample_rate,
                        model=model,
                    )
                    results.extend(flushed_results)
                    if pending_segment is not None:
                        buffer, buffer_start_ms = self._trim_audio_buffer(
                            buffer=buffer,
                            buffer_start_ms=buffer_start_ms,
                            keep_from_ms=pending_segment[0],
                            sample_rate=sample_rate,
                        )

        if pending_segment is not None:
            results.extend(
                self._transcribe_segment_range(
                    model=model,
                    buffer=buffer,
                    buffer_start_ms=buffer_start_ms,
                    start_ms=pending_segment[0],
                    end_ms=pending_segment[1],
                    sample_rate=sample_rate,
                )
            )
        return results

    def _consume_stream_segment(
        self,
        pending_segment: tuple[int, int] | None,
        incoming_segment: tuple[int, int],
        buffer: np.ndarray,
        buffer_start_ms: int,
        sample_rate: int,
        model: Any,
    ) -> tuple[tuple[int, int] | None, list[dict[str, Any]]]:
        if pending_segment is None:
            return incoming_segment, []

        if self._should_merge_segments(pending_segment, incoming_segment):
            merged = (pending_segment[0], incoming_segment[1])
            return merged, []

        flushed_results = self._transcribe_segment_range(
            model=model,
            buffer=buffer,
            buffer_start_ms=buffer_start_ms,
            start_ms=pending_segment[0],
            end_ms=pending_segment[1],
            sample_rate=sample_rate,
        )
        return incoming_segment, flushed_results

    def _should_merge_segments(
        self,
        previous_segment: tuple[int, int],
        current_segment: tuple[int, int],
    ) -> bool:
        gap_ms = current_segment[0] - previous_segment[1]
        merged_duration_ms = current_segment[1] - previous_segment[0]
        return (
            gap_ms <= settings.asr_vad_merge_gap_ms
            and merged_duration_ms <= int(settings.asr_segment_max_seconds * 1000)
        )

    def _transcribe_segment_range(
        self,
        model: Any,
        buffer: np.ndarray,
        buffer_start_ms: int,
        start_ms: int,
        end_ms: int,
        sample_rate: int,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        max_segment_ms = int(settings.asr_segment_max_seconds * 1000)
        for chunk_start_ms, chunk_end_ms in self._split_segment_windows(
            start_ms=start_ms,
            end_ms=end_ms,
            max_segment_ms=max_segment_ms,
        ):
            waveform = self._slice_buffer_waveform(
                buffer=buffer,
                buffer_start_ms=buffer_start_ms,
                start_ms=chunk_start_ms,
                end_ms=chunk_end_ms,
                sample_rate=sample_rate,
            )
            if waveform.size == 0:
                continue

            text = self._transcribe_waveform(model, waveform)
            if not text:
                continue

            results.append(
                {
                    "start": round(chunk_start_ms / 1000.0, 3),
                    "end": round(chunk_end_ms / 1000.0, 3),
                    "text": text,
                }
            )
        return results

    @staticmethod
    def _split_segment_windows(
        start_ms: int,
        end_ms: int,
        max_segment_ms: int,
    ) -> list[tuple[int, int]]:
        if end_ms <= start_ms:
            return []

        windows: list[tuple[int, int]] = []
        cursor = start_ms
        while end_ms - cursor > max_segment_ms:
            windows.append((cursor, cursor + max_segment_ms))
            cursor += max_segment_ms
        windows.append((cursor, end_ms))
        return windows

    @staticmethod
    def _slice_buffer_waveform(
        buffer: np.ndarray,
        buffer_start_ms: int,
        start_ms: int,
        end_ms: int,
        sample_rate: int,
    ) -> np.ndarray:
        start_index = max(0, int((start_ms - buffer_start_ms) * sample_rate / 1000))
        end_index = max(start_index, int((end_ms - buffer_start_ms) * sample_rate / 1000))
        return buffer[start_index:end_index]

    @staticmethod
    def _trim_audio_buffer(
        buffer: np.ndarray,
        buffer_start_ms: int,
        keep_from_ms: int,
        sample_rate: int,
    ) -> tuple[np.ndarray, int]:
        if keep_from_ms <= buffer_start_ms:
            return buffer, buffer_start_ms

        trim_samples = int((keep_from_ms - buffer_start_ms) * sample_rate / 1000)
        if trim_samples <= 0:
            return buffer, buffer_start_ms
        if trim_samples >= buffer.size:
            return np.array([], dtype=np.float32), keep_from_ms
        return buffer[trim_samples:], keep_from_ms

    @staticmethod
    def _pcm16_bytes_to_waveform(frames: bytes, channels: int) -> np.ndarray:
        waveform = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            waveform = waveform.reshape(-1, channels).mean(axis=1)
        return waveform

    @staticmethod
    def _flatten_vad_segments(raw_segments: Any) -> list[tuple[int, int]]:
        flattened: list[tuple[int, int]] = []

        def visit(node: Any) -> None:
            if isinstance(node, (list, tuple)):
                if len(node) == 2 and all(isinstance(item, (int, float)) for item in node):
                    start_ms, end_ms = int(node[0]), int(node[1])
                    if end_ms > start_ms:
                        flattened.append((start_ms, end_ms))
                    return
                for item in node:
                    visit(item)

        visit(raw_segments)
        flattened.sort(key=lambda item: item[0])
        return flattened

    @staticmethod
    def _merge_vad_segments(
        segments: list[tuple[int, int]],
        gap_ms: int,
        max_segment_ms: int,
    ) -> list[tuple[int, int]]:
        if not segments:
            return []

        merged: list[list[int]] = []
        for start_ms, end_ms in sorted(segments, key=lambda item: item[0]):
            if not merged:
                merged.append([start_ms, end_ms])
                continue

            previous = merged[-1]
            can_merge = (
                start_ms - previous[1] <= gap_ms
                and end_ms - previous[0] <= max_segment_ms
            )
            if can_merge:
                previous[1] = max(previous[1], end_ms)
            else:
                merged.append([start_ms, end_ms])

        normalized: list[tuple[int, int]] = []
        for start_ms, end_ms in merged:
            cursor = start_ms
            while end_ms - cursor > max_segment_ms:
                normalized.append((cursor, cursor + max_segment_ms))
                cursor += max_segment_ms
            normalized.append((cursor, end_ms))
        return normalized

    def _transcribe_waveform(self, model: Any, waveform: np.ndarray) -> str:
        raw_result = self._run_inference(model, waveform)
        normalized = self._normalize_segments(raw_result)
        if normalized:
            return " ".join(segment["text"] for segment in normalized if segment["text"]).strip()
        return self._extract_plain_text(raw_result)

    @staticmethod
    def _run_inference(model: Any, audio_input: str | np.ndarray) -> Any:
        if hasattr(model, "transcribe"):
            return model.transcribe(audio_input)
        if hasattr(model, "inference"):
            return model.inference(audio_input)
        if callable(model):
            return model(audio_input)
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
