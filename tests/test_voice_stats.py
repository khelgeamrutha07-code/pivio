import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.voice import aggregate_delivery, count_fillers, delivery_stats, words_per_minute


def test_counts_common_fillers():
    counts = count_fillers("Um, so I was like, you know, basically actually uh doing it")
    assert counts == {"um": 1, "uh": 1, "like": 1, "you know": 1, "basically": 1, "actually": 1, "so": 1}


def test_no_false_positives_inside_words():
    assert count_fillers("The solution unlikely sounds dislike") == {}


def test_words_per_minute():
    assert words_per_minute("one two three four five six", 3) == 120.0
    assert words_per_minute("hello", None) is None
    assert words_per_minute("hello", 0.5) is None


def test_delivery_stats_and_aggregate():
    a = delivery_stats("um I like data", 2)
    b = delivery_stats("so basically it works", None)
    assert a["words"] == 4 and a["filler_total"] == 2 and a["wpm"] == 120.0
    agg = aggregate_delivery([a, b])
    assert agg["answers"] == 2 and agg["filler_total"] == 4 and agg["avg_wpm"] == 120.0
    assert aggregate_delivery([])["answers"] == 0
