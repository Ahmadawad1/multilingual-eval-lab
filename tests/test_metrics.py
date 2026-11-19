import math

import pytest

from backend.metrics import aggregate, paired_bootstrap, retrieval_metrics


def test_hand_calculated_graded_ranking():
    result = retrieval_metrics(["x", "b", "a"], {"a": 3, "b": 1, "c": 2}, k=3)
    assert result["recall"] == pytest.approx(2 / 3)
    assert result["precision"] == pytest.approx(2 / 3)
    assert result["mrr"] == 0.5
    dcg = 1 / math.log2(3) + 7 / 2
    ideal = 7 + 3 / math.log2(3) + 1 / 2
    assert result["ndcg"] == pytest.approx(dcg / ideal)


def test_cutoff_precision_denominator_and_reciprocal_rank():
    assert retrieval_metrics(["a"], {"a": 1}, 5)["precision"] == 0.2
    assert retrieval_metrics(["x", "a"], {"a": 1}, 1) == dict.fromkeys(
        ["recall", "precision", "mrr", "ndcg"], 0
    )
    assert retrieval_metrics([], {"a": 3}, 3)["ndcg"] == 0
    assert retrieval_metrics(["a"], {"a": 3}, 1)["ndcg"] == 1


def test_unjudged_and_queries_without_positive_labels():
    assert retrieval_metrics(["x"], {"a": 0}, 5) is None
    assert retrieval_metrics([], {}, 5) is None
    assert retrieval_metrics(["x", "a"], {"a": 1}, 2)["precision"] == 0.5
    assert aggregate([{"metrics": None}])["ndcg"] is None
    assert (
        aggregate(
            [
                {"metrics": None},
                {"metrics": dict.fromkeys(["recall", "precision", "mrr", "ndcg"], 0.5)},
            ]
        )["recall"]
        == 0.5
    )


@pytest.mark.parametrize("ranking,k", [(["a", "a"], 3), ([], 0)])
def test_invalid_ranking(ranking, k):
    with pytest.raises(ValueError):
        retrieval_metrics(ranking, {"a": 1}, k)


def test_bootstrap_is_paired_reproducible_and_small_sample_aware():
    assert paired_bootstrap([1, 0, 1, 0])["interval"] is None
    assert paired_bootstrap([])["n"] == 0
    assert paired_bootstrap([0.25] * 8)["interval"] == [0.25, 0.25]
    values = [-1, 0, 0.25, 0.5, 1, -0.25]
    first = paired_bootstrap(values)
    assert first == paired_bootstrap(values)
    low, high = first["interval"]
    assert -1 <= low < sum(values) / len(values) < high <= 1
