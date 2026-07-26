# Notebooks

Plan §8 lists five notebooks. They are not committed as empty stubs — an empty
`.ipynb` is noise in a diff and tells the next reader nothing. This file records what
each one is for, and each is created when its phase begins.

**Rule: notebooks call into `src/daloy/`; they do not own logic.** Anything worth
re-running is worth testing, and a function that only exists in a cell cannot be
tested. When a notebook grows a function that matters, move it to `src/daloy/` and
import it back.

| Notebook | Phase | Purpose | Depends on |
|---|---|---|---|
| `01_pdf_parsing_audit.ipynb` | 1 | Audit which harvested PDFs have a real text layer and which need OCR. Extract the ordinance provisions that key the rules table. | `scrapers.cainta_ordinances`, `scrapers.nswmc_reports`, `pdfplumber` |
| `02_feature_extraction.ipynb` | 5 | Build the three feature tiers from plan §4.1 — hand-crafted (~250-d), transfer embeddings (576–1280-d), PCA-reduced (~100-d). | `scikit-image`, `Pillow`, a frozen MobileNetV3 |
| `03_pcc_baseline.ipynb` | 5 | Compute the Proportional Chance Criterion and the 1.25× threshold **before** any modelling. | `daloy.metrics` |
| `04_model_bakeoff.ipynb` | 5 | kNN, logistic regression, SVM-RBF, Random Forest, gradient boosting, fine-tuned MobileNetV3 — across all three feature tiers. The comparison is the methodological contribution. | `scikit-learn` |
| `05_cainta_holdout_eval.ipynb` | 5 | Evaluate on Cainta-collected images that never entered training. **The only honest measure of transfer.** | `daloy.metrics.evaluation_report` |

## Two things notebook 03 exists to prevent

**Accuracy is close to meaningless here.** The waste taxonomy is heavily imbalanced, so
a classifier that learns nothing but the class prior can post a respectable-looking
number. `daloy.metrics.chance_baseline` computes what chance actually scores on your
split, and flags the case where 1.25 × PCC lands above 1.0 — at which point the gate is
unpassable by any model and the split itself is the problem.

**Sachet recall must never hide inside a headline average.**
`daloy.metrics.evaluation_report` breaks out `plastic_film_sachet` separately, and says
so explicitly when a split contains no sachet samples at all — because a holdout that
cannot measure the blind spot must not read as a clean pass.

## Before running 05

The Cainta holdout must never have entered training, at any stage, including
hyperparameter selection. Expect a large drop from published TACO benchmarks. That drop
is the finding, not a failure — it is the number that says whether transfer from
European litter imagery works on Philippine household waste.
