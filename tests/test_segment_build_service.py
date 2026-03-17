from app.services.gemini import SegmentBuildService


def test_fallback_segments_merge_consecutive_shots_into_intervals() -> None:
    service = SegmentBuildService()
    shots = [
        {"shot_index": 0, "start": 0.0, "end": 2.0},
        {"shot_index": 1, "start": 2.0, "end": 4.0},
        {"shot_index": 2, "start": 4.0, "end": 6.5},
        {"shot_index": 3, "start": 6.5, "end": 11.0},
        {"shot_index": 4, "start": 11.0, "end": 16.0},
    ]
    asr_segments = [
        {"start": 0.0, "end": 3.5, "text": "第一句还没结束"},
        {"start": 3.5, "end": 6.5, "text": "现在结束。"},
        {"start": 6.5, "end": 11.0, "text": "第二段继续"},
        {"start": 11.0, "end": 16.0, "text": "第二段收尾。"},
    ]

    segments = service._fallback_segments(shots, asr_segments)

    assert [segment["shot_indexes"] for segment in segments] == [[0, 1, 2, 3], [4]]
    assert segments[0]["start"] == 0.0
    assert segments[0]["end"] == 11.0
    assert segments[1]["start"] == 11.0
    assert segments[1]["end"] == 16.0
