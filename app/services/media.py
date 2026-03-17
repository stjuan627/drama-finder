from __future__ import annotations

import json
import subprocess
from pathlib import Path


class FFmpegService:
    def extract_audio(self, video_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg",
            "-y",
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
        subprocess.run(command, check=True, capture_output=True)
        return output_path

    def extract_frames(self, video_path: Path, output_dir: Path, fps: int = 1) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        pattern = output_dir / "frame_%06d.jpg"
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps}",
            str(pattern),
        ]
        subprocess.run(command, check=True, capture_output=True)
        return sorted(output_dir.glob("frame_*.jpg"))

    def probe_duration(self, video_path: Path) -> float:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video_path),
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        payload = json.loads(result.stdout)
        return float(payload["format"]["duration"])
