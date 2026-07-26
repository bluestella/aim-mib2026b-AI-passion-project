# Data

Four stages, one rule each.

| Directory | Rule |
|---|---|
| `raw/` | **Immutable. Never edit.** Exactly as fetched. Reproducible by re-running the scrapers. |
| `interim/` | Parsed PDFs and normalised API responses. Regenerable — safe to delete. |
| `processed/` | Model-ready tables. What the notebooks and the app consume. |
| `external/` | TACO, TrashNet, OpenLitterMap. Third-party, separately licensed. |

Contents are gitignored; the directory structure is not. The one exception is
`raw/_manifest.jsonl`, which **is** committed.

## The manifest

Every fetch appends a row:

```json
{"source_id": "nswmc_reports", "url": "https://...", "path": "data/raw/...",
 "sha256": "...", "content_type": "application/pdf", "fetched_at": "2026-07-26T..."}
```

This is what makes plan §7.8 enforceable. Any figure that reaches a slide can be traced
back to a URL and a date, and the `sha256` catches a government PDF that was silently
revised in place. If the MENRO later disputes a number, the answer is an audit trail
rather than an argument.

## External datasets

Not committed — large, externally hosted, and separately licensed. Fetch them yourself:

| Dataset | Source | License |
|---|---|---|
| TACO | `tacodataset.org` | CC BY 4.0 — **attribution required** |
| TrashNet | GitHub (Stanford, Yang et al. 2016) | Open |
| OpenLitterMap | `openlittermap.com` | Check per-image |
| AquaTrash | GitHub | Open |

Expect a large accuracy drop when transferring any of these to Philippine imagery.
That is what the Cainta holdout set measures, and it is the only honest number in the
whole evaluation.

## Personal data

`processed/` must never contain a raw user coordinate. Bin through
`daloy.spatial.bin_point` at the point of collection — the cell ID is what gets stored,
and the coordinate is not persisted anywhere (plan §7.5).

Junkshop coordinates are different: those are business premises, not personal data, and
they are meant to be published — and contributed back to OSM under ODbL.
