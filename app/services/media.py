from __future__ import annotations

import json
from numbers import Real
import subprocess
from pathlib import Path


class FFmpegService:
    def extract_audio(self, video_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_path),
        ]
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )
        return output_path

    def extract_frames(
        self,
        video_path: Path,
        output_dir: Path,
        fps: int | float | str = 1,
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        for existing in output_dir.glob("frame_*.jpg"):
            existing.unlink()

        pattern = output_dir / "frame_%06d.jpg"
        fps_expr = (
            str(int(fps))
            if isinstance(fps, Real) and float(fps).is_integer()
            else str(fps)
        )
        command = [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps_expr}",
            str(pattern),
        ]
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )
        return sorted(output_dir.glob("frame_*.jpg"))

    def extract_frame_at_timestamp(self, video_path: Path, output_path: Path, timestamp: float) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-ss",
            f"{max(timestamp, 0.0):.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(output_path),
        ]
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )
        return output_path

    def probe_duration(self, video_path: Path) -> float:
        command = [
            "ffprobe",
            "-nostdin",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video_path),
        ]
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        payload = json.loads(result.stdout)
        return float(payload["format"]["duration"])
