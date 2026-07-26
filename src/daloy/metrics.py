"""Baselines and honest reporting for the Stage-1 classifier (plan §5.4).

The waste taxonomy is heavily imbalanced, and on imbalanced data a headline
accuracy figure flatters a model that has learned nothing but the class prior.
The Proportional Chance Criterion is the guard: PCC is the accuracy a
classifier would reach by guessing in proportion to the class distribution, and
the conventional practical threshold is 1.25 x PCC.

Plan §9 sets the Phase-5 gate as macro-F1 > 1.25 x PCC on a Cainta-collected
holdout that never entered training. This module computes both sides of that
comparison, plus the per-class recall that the headline number hides -- above
all for ``plastic_film_sachet``, the class the plan expects the model to be
most confidently wrong about.

Pure stdlib on purpose, so the baseline can be computed before anyone installs
a modelling stack.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

#: Conventional multiplier applied to PCC to get a "meaningfully better than
#: chance" threshold.
PRACTICAL_MULTIPLIER = 1.25


@dataclass(frozen=True)
class ChanceBaseline:
    pcc: float
    practical_threshold: float
    majority_class: str
    majority_rate: float
    n: int
    class_proportions: dict[str, float]

    def beats_chance(self, score: float) -> bool:
        return score > self.practical_threshold

    @property
    def threshold_is_attainable(self) -> bool:
        """False when 1.25 x PCC exceeds 1.0.

        On a severely imbalanced split the practical threshold can land above
        perfect accuracy, at which point the gate is unpassable by any model
        and the split itself is the problem. Worth catching before someone
        spends a phase trying to clear an impossible bar.
        """
        return self.practical_threshold <= 1.0

    def summary(self) -> str:
        lines = [
            f"n = {self.n}, classes = {len(self.class_proportions)}",
            f"PCC (proportional chance)   : {self.pcc:.4f}",
            f"1.25 x PCC (practical gate) : {self.practical_threshold:.4f}",
            f"Majority-class accuracy     : {self.majority_rate:.4f} "
            f"({self.majority_class})",
            "",
            "Class distribution:",
        ]
        for label, share in sorted(
            self.class_proportions.items(), key=lambda kv: -kv[1]
        ):
            lines.append(f"  {label:22s} {share:6.2%}")
        if not self.threshold_is_attainable:
            lines.append(
                "\nWarning: 1.25 x PCC exceeds 1.0, so no model can clear this gate."
                "\nThe split is too imbalanced for the criterion to mean anything --"
                "\nrebalance the corpus or evaluate on macro-F1 alone."
            )
        elif self.majority_rate > self.practical_threshold:
            lines.append(
                "\nNote: majority-class guessing already clears 1.25 x PCC here."
                "\nAccuracy is not a usable headline metric on this split -- report"
                "\nmacro-F1 and per-class recall instead."
            )
        return "\n".join(lines)


def chance_baseline(labels: Iterable[str]) -> ChanceBaseline:
    """Compute PCC and the majority-class baseline from a label column.

    PCC = sum of squared class proportions.
    """
    counts = Counter(labels)
    n = sum(counts.values())
    if n == 0:
        raise ValueError("Cannot compute a baseline from zero labels.")

    proportions = {label: count / n for label, count in counts.items()}
    pcc = sum(share**2 for share in proportions.values())
    majority_class, majority_count = counts.most_common(1)[0]

    return ChanceBaseline(
        pcc=pcc,
        practical_threshold=PRACTICAL_MULTIPLIER * pcc,
        majority_class=majority_class,
        majority_rate=majority_count / n,
        n=n,
        class_proportions=proportions,
    )


def confusion_matrix(
    y_true: Sequence[str], y_pred: Sequence[str]
) -> tuple[list[str], list[list[int]]]:
    """Return (ordered labels, matrix) with rows = truth, columns = prediction."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must be the same length.")
    labels = sorted(set(y_true) | set(y_pred))
    index = {label: i for i, label in enumerate(labels)}
    matrix = [[0] * len(labels) for _ in labels]
    for truth, prediction in zip(y_true, y_pred, strict=True):
        matrix[index[truth]][index[prediction]] += 1
    return labels, matrix


def per_class_scores(
    y_true: Sequence[str], y_pred: Sequence[str]
) -> dict[str, dict[str, float]]:
    """Precision, recall, F1 and support for every class."""
    labels, matrix = confusion_matrix(y_true, y_pred)
    scores: dict[str, dict[str, float]] = {}

    for i, label in enumerate(labels):
        true_positive = matrix[i][i]
        support = sum(matrix[i])
        predicted = sum(row[i] for row in matrix)
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / support if support else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        scores[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
    return scores


def macro_f1(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    """Unweighted mean F1 across classes.

    Unweighted is the point: it refuses to let a large, easy class such as PET
    compensate for a small, critical one such as sachet.
    """
    scores = per_class_scores(y_true, y_pred)
    if not scores:
        return 0.0
    return sum(s["f1"] for s in scores.values()) / len(scores)


def accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must be the same length.")
    if not y_true:
        return 0.0
    return sum(t == p for t, p in zip(y_true, y_pred, strict=True)) / len(y_true)


def evaluation_report(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    *,
    critical_classes: Sequence[str] = ("plastic_film_sachet",),
) -> str:
    """Full honest report: baseline, headline metrics, per-class, critical classes.

    ``critical_classes`` are broken out separately because plan §10 requires
    sachet recall to be reported on its own and never allowed to hide inside a
    headline average.
    """
    baseline = chance_baseline(y_true)
    scores = per_class_scores(y_true, y_pred)
    acc = accuracy(y_true, y_pred)
    macro = macro_f1(y_true, y_pred)

    lines = [
        "=" * 62,
        "STAGE-1 EVALUATION",
        "=" * 62,
        baseline.summary(),
        "",
        "-" * 62,
        f"Accuracy  : {acc:.4f}",
        f"Macro-F1  : {macro:.4f}",
        f"Gate (macro-F1 > 1.25 x PCC = {baseline.practical_threshold:.4f}): "
        f"{'PASS' if baseline.beats_chance(macro) else 'FAIL'}",
        "",
        f"{'class':22s} {'prec':>7s} {'recall':>7s} {'f1':>7s} {'n':>6s}",
    ]
    for label, score in sorted(scores.items()):
        lines.append(
            f"{label:22s} {score['precision']:7.3f} {score['recall']:7.3f} "
            f"{score['f1']:7.3f} {int(score['support']):6d}"
        )

    lines.append("")
    lines.append("-" * 62)
    lines.append("CRITICAL CLASSES (reported separately, per plan §10)")
    for label in critical_classes:
        if label not in scores:
            lines.append(f"  {label}: ABSENT from this split — the blind spot is unmeasured.")
            continue
        score = scores[label]
        lines.append(
            f"  {label}: recall {score['recall']:.3f} on {int(score['support'])} sample(s)"
        )
        if score["support"] < 400:
            lines.append(
                "    Below the plan's Phase-4 gate of 400 sachet images. "
                "Treat this recall as provisional."
            )
    return "\n".join(lines)
