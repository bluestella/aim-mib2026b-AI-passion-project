"""Tests for the PCC baseline and honest-reporting helpers (plan §5.4)."""

from __future__ import annotations

import pytest

from daloy.metrics import (
    accuracy,
    chance_baseline,
    confusion_matrix,
    evaluation_report,
    macro_f1,
    per_class_scores,
)


def test_pcc_of_a_balanced_two_class_split() -> None:
    """PCC = sum p_i^2; for a 50/50 split that is 0.5."""
    baseline = chance_baseline(["a", "b"] * 50)
    assert baseline.pcc == pytest.approx(0.5)
    assert baseline.practical_threshold == pytest.approx(0.625)


def test_pcc_rises_with_imbalance() -> None:
    """The trap the plan warns about: imbalance inflates the chance baseline."""
    balanced = chance_baseline(["a", "b"] * 50)
    skewed = chance_baseline(["a"] * 90 + ["b"] * 10)
    assert skewed.pcc > balanced.pcc
    assert skewed.pcc == pytest.approx(0.9**2 + 0.1**2)


def test_dominant_class_in_a_long_tail_makes_accuracy_unusable() -> None:
    """The shape the waste taxonomy actually has: one big class, a long tail.

    PET at 50% with ten small classes behind it. Majority guessing scores 0.50
    against a practical threshold of ~0.34, so accuracy alone would flatter a
    model that never predicts anything but PET.
    """
    labels = ["PET_bottle"] * 50 + [f"class_{i}" for i in range(10) for _ in range(5)]
    baseline = chance_baseline(labels)
    assert baseline.n == 100
    assert baseline.majority_rate == pytest.approx(0.5)
    assert baseline.pcc == pytest.approx(0.275)
    assert baseline.majority_rate > baseline.practical_threshold
    assert "not a usable headline metric" in baseline.summary()


def test_severe_imbalance_makes_the_gate_unattainable() -> None:
    """At 90/10 the practical threshold is 1.025 — above perfect accuracy.

    No model can clear that, so the criterion has stopped being informative and
    the split needs rebalancing. The report has to say so rather than let a
    phase be spent chasing it.
    """
    baseline = chance_baseline(["a"] * 90 + ["b"] * 10)
    assert baseline.pcc == pytest.approx(0.82)
    assert baseline.practical_threshold > 1.0
    assert not baseline.threshold_is_attainable
    assert "no model can clear this gate" in baseline.summary()


def test_balanced_split_gate_is_attainable() -> None:
    assert chance_baseline(["a", "b"] * 50).threshold_is_attainable


def test_empty_labels_rejected() -> None:
    with pytest.raises(ValueError):
        chance_baseline([])


def test_confusion_matrix_orients_truth_by_row() -> None:
    labels, matrix = confusion_matrix(["a", "a", "b"], ["a", "b", "b"])
    assert labels == ["a", "b"]
    assert matrix == [[1, 1], [0, 1]]


def test_per_class_scores_on_a_worked_example() -> None:
    y_true = ["a", "a", "a", "b"]
    y_pred = ["a", "a", "b", "b"]
    scores = per_class_scores(y_true, y_pred)
    assert scores["a"]["recall"] == pytest.approx(2 / 3)
    assert scores["a"]["precision"] == pytest.approx(1.0)
    assert scores["b"]["precision"] == pytest.approx(0.5)
    assert scores["b"]["support"] == 1


def test_macro_f1_refuses_to_let_the_big_class_carry_the_score() -> None:
    """A model that ignores the rare class: high accuracy, poor macro-F1."""
    y_true = ["PET_bottle"] * 95 + ["plastic_film_sachet"] * 5
    y_pred = ["PET_bottle"] * 100
    assert accuracy(y_true, y_pred) == pytest.approx(0.95)
    assert macro_f1(y_true, y_pred) < 0.5


def test_mismatched_lengths_rejected() -> None:
    with pytest.raises(ValueError):
        confusion_matrix(["a", "b"], ["a"])


def test_report_breaks_out_the_sachet_class() -> None:
    y_true = ["PET_bottle"] * 95 + ["plastic_film_sachet"] * 5
    y_pred = ["PET_bottle"] * 100
    report = evaluation_report(y_true, y_pred)
    assert "CRITICAL CLASSES" in report
    assert "plastic_film_sachet: recall 0.000" in report
    assert "Below the plan's Phase-4 gate of 400" in report


def test_report_says_so_when_the_blind_spot_is_unmeasured() -> None:
    """A holdout with no sachet samples must not read as a clean pass."""
    report = evaluation_report(["PET_bottle"] * 10, ["PET_bottle"] * 10)
    assert "ABSENT from this split" in report
