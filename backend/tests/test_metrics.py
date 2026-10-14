import pytest

from app.ml.metrics import micro_prf, ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank


def test_ranking_metrics():
    labels = [2, 0, 1, 0, 0, 2]
    assert precision_at_k(labels, 5) == pytest.approx(2 / 5)
    assert recall_at_k(labels, 5) == pytest.approx(2 / 3)
    assert reciprocal_rank([0, 0, 1]) == pytest.approx(1 / 3)
    assert ndcg_at_k(sorted(labels, reverse=True), 10) == pytest.approx(1.0)
    assert 0 < ndcg_at_k(labels, 10) < 1


def test_undefined_metrics_return_none():
    assert recall_at_k([0, 0], 10) is None
    assert ndcg_at_k([0, 0], 10) is None


def test_micro_prf():
    result = micro_prf([({"python", "sql"}, {"python", "excel"})])
    assert result["precision"] == 0.5 and result["recall"] == 0.5 and result["tp"] == 1
