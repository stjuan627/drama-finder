from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from app.db.session import SessionLocal
from app.schemas.search import SearchHit
from app.services.retrieval import RetrievalService


@dataclass(slots=True)
class EvalSample:
    sample_id: str
    series_id: str
    episode_id: str
    query_type: str
    gt_start_ts: float
    gt_end_ts: float
    image_path: str | None = None
    query_text: str | None = None
    top_k: int = 5


def load_samples(dataset_path: Path) -> list[EvalSample]:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("dataset must be a JSON array")

    samples: list[EvalSample] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"sample at index {index} must be an object")
        sample_id = str(item.get("sample_id") or f"sample-{index + 1}")
        samples.append(
            EvalSample(
                sample_id=sample_id,
                series_id=str(item["series_id"]),
                episode_id=str(item["episode_id"]),
                query_type=str(item["query_type"]),
                image_path=item.get("image_path"),
                query_text=item.get("query_text"),
                gt_start_ts=float(item["gt_start_ts"]),
                gt_end_ts=float(item["gt_end_ts"]),
                top_k=int(item.get("top_k", 5)),
            )
        )
    return samples


def interval_intersection(
    pred_start_ts: float,
    pred_end_ts: float,
    gt_start_ts: float,
    gt_end_ts: float,
) -> float:
    return max(0.0, min(pred_end_ts, gt_end_ts) - max(pred_start_ts, gt_start_ts))


def interval_coverage(
    pred_start_ts: float,
    pred_end_ts: float,
    gt_start_ts: float,
    gt_end_ts: float,
) -> float:
    gt_duration = max(0.0, gt_end_ts - gt_start_ts)
    if gt_duration <= 0:
        return 0.0
    return interval_intersection(pred_start_ts, pred_end_ts, gt_start_ts, gt_end_ts) / gt_duration


def is_interval_hit(hit: SearchHit, sample: EvalSample) -> bool:
    if hit.series_id != sample.series_id or hit.episode_id != sample.episode_id:
        return False
    return (
        interval_intersection(
            hit.matched_start_ts,
            hit.matched_end_ts,
            sample.gt_start_ts,
            sample.gt_end_ts,
        )
        > 0
    )


def evaluate_sample(sample: EvalSample, hits: list[SearchHit]) -> dict[str, Any]:
    top_k_hits = hits[: sample.top_k]
    top1_hit = top_k_hits[0] if top_k_hits else None
    top1_correct = bool(top1_hit and is_interval_hit(top1_hit, sample))
    topk_correct = any(is_interval_hit(hit, sample) for hit in top_k_hits)

    best_coverage = 0.0
    best_hit: SearchHit | None = None
    for hit in top_k_hits:
        coverage = interval_coverage(
            hit.matched_start_ts,
            hit.matched_end_ts,
            sample.gt_start_ts,
            sample.gt_end_ts,
        )
        if coverage > best_coverage:
            best_coverage = coverage
            best_hit = hit

    return {
        "sample_id": sample.sample_id,
        "query_type": sample.query_type,
        "top1_correct": top1_correct,
        "topk_correct": topk_correct,
        "coverage": round(best_coverage, 4),
        "best_hit": (
            {
                "series_id": best_hit.series_id,
                "episode_id": best_hit.episode_id,
                "matched_start_ts": best_hit.matched_start_ts,
                "matched_end_ts": best_hit.matched_end_ts,
                "score": best_hit.score,
            }
            if best_hit
            else None
        ),
    }


def summarize_results(results: list[dict[str, Any]], top_k: int) -> dict[str, Any]:
    total = len(results)
    if total == 0:
        return {
            "dataset_size": 0,
            "top1_hit_rate": 0.0,
            f"top{top_k}_hit_rate": 0.0,
            "mean_coverage": 0.0,
            "failure_samples": [],
        }

    top1_hit_rate = sum(1 for item in results if item["top1_correct"]) / total
    topk_hit_rate = sum(1 for item in results if item["topk_correct"]) / total
    mean_coverage = mean(item["coverage"] for item in results)
    failure_samples = [item for item in results if not item["topk_correct"]]

    return {
        "dataset_size": total,
        "top1_hit_rate": round(top1_hit_rate, 4),
        f"top{top_k}_hit_rate": round(topk_hit_rate, 4),
        "mean_coverage": round(mean_coverage, 4),
        "failure_samples": failure_samples,
    }


def run_evaluation(dataset_path: Path) -> dict[str, Any]:
    samples = load_samples(dataset_path)
    retrieval_service = RetrievalService()
    results: list[dict[str, Any]] = []
    max_top_k = max((sample.top_k for sample in samples), default=5)

    with SessionLocal() as db:
        for sample in samples:
            if sample.query_type == "image":
                if not sample.image_path:
                    raise ValueError(f"{sample.sample_id} missing image_path")
                response = retrieval_service.search_image(
                    db,
                    Path(sample.image_path).expanduser().resolve(),
                    limit=sample.top_k,
                )
            elif sample.query_type == "text":
                if not sample.query_text:
                    raise ValueError(f"{sample.sample_id} missing query_text")
                response = retrieval_service.search_text(db, sample.query_text, limit=sample.top_k)
            else:
                raise ValueError(f"unsupported query_type: {sample.query_type}")
            results.append(evaluate_sample(sample, response.hits))

    return {
        "dataset_path": str(dataset_path.resolve()),
        "summary": summarize_results(results, top_k=max_top_k),
        "results": results,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate interval retrieval quality.")
    parser.add_argument("dataset", help="Path to evaluation dataset JSON file")
    parser.add_argument(
        "--output",
        help="Optional path to write evaluation result JSON",
        default="",
    )
    args = parser.parse_args()

    report = run_evaluation(Path(args.dataset).expanduser().resolve())
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)

    if args.output:
        Path(args.output).expanduser().resolve().write_text(output, encoding="utf-8")
