"""DALOY Scan — shared logic for the Cainta zero-waste app.

Notebooks call into this package; they do not own logic. Everything here is
importable and unit-testable, which is the difference between an analysis that
can be re-run and one that can only be re-read.

Modules
-------
rules_engine
    The Stage-2 decision layer: material_class + local rules -> disposal
    pathway. A rules table, deliberately not a classifier (plan §5.2).
metrics
    Proportional Chance Criterion and the honest-reporting helpers that go
    with it (plan §5.4).
spatial
    Privacy-bounded spatial binning. The n=7 barangay problem lives here.
"""

__version__ = "0.1.0"
