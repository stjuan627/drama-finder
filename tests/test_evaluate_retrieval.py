from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.search import SearchHit
from scripts.evaluate_retrieval import (
    EvalSample,
    evaluate_sample,
    interval_coverage,
    interval_intersection,
    summarize_results,
)


def test_interval_intersection_and_coverage() -> None:
    assert interval_intersection(10.0, 20.0, 15.0, 25.0) == 5.0
    assert interval_intersection(10.0, 12.0, 13.0, 25.0) == 0.0
    assert interval_coverage(10.0, 20.0, 15.0, 25.0) == 0.5


def test_evaluate_sample_marks_top1_and_topk_hits() -> None:
    sample = EvalSample(
        sample_id="s1",
        series_id="series-1",
        episode_id="ep01",
        query_type="text",
        query_text="测试台词",
        gt_start_ts=15.0,
        gt_end_ts=25.0,
        top_k=3,
    )
    hits = [
        SearchHit(
            series_id="series-1",
            episode_id="ep01",
            series_label="测试剧 S1",
            episode_label="第1集 · 第一集",
            matched_start_ts=10.0,
            matched_end_ts=20.0,
            score=0.9,
            evidence_images=[],
            evidence_text=["a"],
        ),
        SearchHit(
            series_id="series-1",
            episode_id="ep01",
            series_label="测试剧 S1",
            episode_label="第1集 · 第一集",
            matched_start_ts=30.0,
            matched_end_ts=40.0,
            score=0.7,
            evidence_images=[],
            evidence_text=["b"],
        ),
    ]

    result = evaluate_sample(sample, hits)

    assert result["top1_correct"] is True
    assert result["topk_correct"] is True
    assert result["coverage"] == 0.5


def test_summarize_results_counts_failures() -> None:
    summary = summarize_results(
        [
            {"sample_id": "a", "top1_correct": True, "topk_correct": True, "coverage": 0.8},
            {"sample_id": "b", "top1_correct": False, "topk_correct": False, "coverage": 0.0},
        ],
        top_k=5,
    )

    assert summary["dataset_size"] == 2
    assert summary["top1_hit_rate"] == 0.5
    assert summary["top5_hit_rate"] == 0.5
    assert summary["mean_coverage"] == 0.4
    assert len(summary["failure_samples"]) == 1
