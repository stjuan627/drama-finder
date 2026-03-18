from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path

HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f3efe7;
      --card: #fffaf2;
      --line: #d6c9b6;
      --text: #2f2419;
      --muted: #7b6a57;
      --accent: #8c4c2f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      background: radial-gradient(circle at top, #f8f3ea, var(--bg));
      color: var(--text);
    }}
    .wrap {{
      width: min(1500px, calc(100vw - 32px));
      margin: 24px auto 40px;
    }}
    .hero {{
      padding: 24px 28px;
      background: linear-gradient(135deg, rgba(140, 76, 47, 0.12), rgba(255,255,255,0.75));
      border: 1px solid var(--line);
      border-radius: 20px;
      margin-bottom: 24px;
      box-shadow: 0 14px 32px rgba(79, 55, 33, 0.08);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      line-height: 1.2;
    }}
    .meta {{
      color: var(--muted);
      font-size: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 12px 24px rgba(72, 48, 26, 0.06);
    }}
    .card-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 12px;
    }}
    .shot-id {{
      font-size: 18px;
      font-weight: 700;
      color: var(--accent);
    }}
    .time {{
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    .frames {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    figure {{
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    img {{
      width: 100%;
      aspect-ratio: 16 / 9;
      object-fit: cover;
      border-radius: 12px;
      border: 1px solid #ccbda7;
      background: #e8dfd2;
    }}
    figcaption {{
      font-size: 12px;
      color: var(--muted);
      text-align: center;
    }}
    @media (max-width: 960px) {{
      .frames {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>{title}</h1>
      <div class="meta">shots: {shot_count} | 来源: {shots_path}</div>
    </section>
    <section class="grid">
      {cards}
    </section>
  </main>
</body>
</html>
"""


def ts_to_label(seconds: float) -> str:
    whole = max(0, int(seconds))
    hh = whole // 3600
    mm = (whole % 3600) // 60
    ss = whole % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def frame_path(frames_dir: Path, second_index: int) -> Path:
    return frames_dir / f"frame_{second_index + 1:06d}.jpg"


def resolve_three_frames(
    frames_dir: Path,
    start_ts: float,
    end_ts: float,
) -> list[tuple[str, Path]]:
    mid_ts = (start_ts + end_ts) / 2
    candidates = [
        ("start", frame_path(frames_dir, int(start_ts))),
        ("mid", frame_path(frames_dir, int(mid_ts))),
        ("end", frame_path(frames_dir, max(int(end_ts) - 1, int(start_ts)))),
    ]
    return candidates


def build_card(shot: dict, frames_dir: Path, output_dir: Path) -> str:
    shot_index = shot["shot_index"]
    start_ts = float(shot["start"])
    end_ts = float(shot["end"])
    figures: list[str] = []
    for label, img_path in resolve_three_frames(frames_dir, start_ts, end_ts):
        caption_ts = (
            start_ts
            if label == "start"
            else end_ts if label == "end" else (start_ts + end_ts) / 2
        )
        if img_path.exists():
            rel = Path(os.path.relpath(img_path, output_dir))
            figures.append(
                f"<figure><img src=\"{html.escape(rel.as_posix())}\" "
                f"alt=\"shot {shot_index} {label}\">"
                f"<figcaption>{label} · {ts_to_label(caption_ts)}</figcaption></figure>"
            )
        else:
            figures.append(
                "<figure>"
                "<div style=\"aspect-ratio:16/9;border:1px dashed #ccbda7;"
                "border-radius:12px;\"></div>"
                f"<figcaption>{label} · missing</figcaption></figure>"
            )
    return (
        "<article class=\"card\">"
        f"<div class=\"card-head\"><div class=\"shot-id\">shot #{shot_index}</div>"
        f"<div class=\"time\">{ts_to_label(start_ts)} - {ts_to_label(end_ts)} "
        f"({end_ts - start_ts:.2f}s)</div></div>"
        f"<div class=\"frames\">{''.join(figures)}</div>"
        "</article>"
    )


def generate(shots_path: Path, frames_dir: Path, output_path: Path) -> None:
    shots = json.loads(shots_path.read_text(encoding="utf-8"))
    cards = [build_card(shot, frames_dir, output_path.parent) for shot in shots]
    output_path.write_text(
        HTML_TEMPLATE.format(
            title=f"Shot QA - {shots_path.parent.parent.name}",
            shot_count=len(shots),
            shots_path=html.escape(str(shots_path)),
            cards="".join(cards),
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local HTML QA gallery for shots.")
    parser.add_argument("--shots", required=True, help="Path to shots.json")
    parser.add_argument("--frames-dir", required=True, help="Directory containing extracted frames")
    parser.add_argument("--output", required=True, help="Output HTML path")
    args = parser.parse_args()

    shots_path = Path(args.shots).resolve()
    frames_dir = Path(args.frames_dir).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate(shots_path, frames_dir, output_path)


if __name__ == "__main__":
    main()
