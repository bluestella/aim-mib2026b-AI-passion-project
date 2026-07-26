# Project DALOY Scan

**Saan napupunta ang basura natin?**

A zero-waste web application for **Cainta, Rizal**. Photograph an item of waste and see
the two futures of that object in Cainta specifically: the leakage path (your street →
barangay drainage → creek → Manggahan Floodway → Laguna de Bay) and the recovery path
(nearest junkshop or MRF, current ₱/kg, next barangay pickup).

The full reasoning lives in **[docs/DATA_AND_ML_PLAN.md](docs/DATA_AND_ML_PLAN.md)**.
Read §0 before anything else.

---

## The short version

Stage 1 — *what material is this?* — is a commodity. TACO and TrashNet solve it and
anyone can ship it. Stage 2 — *where does this material go in this municipality, who
buys it, for how much* — has never been assembled for Cainta.

**Stage 2 is the moat**, and this repository is built around that: a rules engine and a
local knowledge graph first, machine learning second.

---

## What is built

| Phase | | Status |
|---|---|---|
| — | Planning document (§0–§11 + Appendix A) | Complete |
| 0 | FOI request drafts and deadline tracker | Drafted, ready to file |
| 0 | Scraper toolkit with governance enforced in code | Built, offline-tested |
| 1 | Ordinance / NSWMC harvest | **Blocked — no network access to the source hosts** |
| 1 | Disposal rules table (11 classes, bilingual) | Built — **all legal citations `unverified`** |
| 2 | Junkshop field survey instrument | Drafted — fieldwork not started |
| 3 | **Rules-only PWA (`web/`)** | **Built, browser-verified, Vercel-ready** |
| 4–6 | Corpus, model bake-off, classifier (`models/`) | Not started |

The plan sequences ML into v2 deliberately. **Phase 3 ships a genuinely useful product
with zero machine learning** — and it now runs. If Phases 4–6 never happen, Cainta still
gets the first machine-readable map of where its waste actually goes.

Phases 1, 2 and 4 are blocked on things code cannot supply: network access to
`cainta.gov.ph` and `nswmc.emb.gov.ph`, two weekends of junkshop fieldwork, and a school
partnership. The scrapers are written and tested against fixtures; they degrade loudly
rather than silently when the network refuses them.

---

## Quickstart

```bash
pip install -e ".[dev]"
pytest
```

Run the app:

```bash
python scripts/build_app_data.py   # compile rules/*.yaml -> web/src/data/rules.json
cd web && npm install && npm run dev
```

Pick a barangay, tap `sachet`, and watch it reach Laguna de Bay. See
[web/README.md](web/README.md) for the invariants that screen enforces and for the
one Vercel setting the deploy needs.

Ask the rules engine the same question from the CLI:

```bash
python -m daloy.rules_engine bote      # PET bottle — sell to junkshop, ~PHP 10-14/kg
python -m daloy.rules_engine sachet    # no market, residual, flagged critical
python -m daloy.rules_engine --audit   # how much of the rules table is still provisional
```

`--audit` currently reports **0 of 6 legal sources verified**. That is correct and
deliberate — see "Verification state" below.

Harvest data (each honours robots.txt, a 2s rate limit, and content-hash caching):

```bash
export DALOY_CONTACT_EMAIL="you@example.org"   # goes in the User-Agent
python -m scrapers.cainta_ordinances --dry-run  # list PDFs, download nothing
python -m scrapers.nswmc_reports
python -m scrapers.osm_overpass --print-query
python -m scrapers.foi_tracker status
```

---

## Verification state — read this before quoting any number

Every legal citation in `rules/cainta_disposal_rules.yaml` currently carries
`verification: unverified`, and every price carries `confidence: low`. These are values
taken from the planning document — **what we expect to find, not what we have
confirmed.**

`Pathway.is_presentable_as_official` returns `False` while that is true, and the UI must
gate on it. The app may show the guidance; it may not attribute it to the municipality
until the ordinance PDF has been retrieved and read (plan §7.8).

Phase 1 closes this by harvesting the ordinances and flipping each source to
`harvested` with a `retrieved_on` date. A test asserts the guardrail holds, so relaxing
it requires a conscious change in a diff.

---

## Layout

```
docs/            Plan, data dictionary, privacy notice, FOI drafts, field survey form
scrapers/        Data harvesters — governance enforced in scrapers/common.py
rules/           cainta_disposal_rules.yaml — the Stage-2 decision layer
                 cainta_flow_schematic.yaml — Flow Simulation stages (schematic)
src/daloy/       rules_engine · metrics (PCC) · spatial (H3 binning)
scripts/         build_app_data.py (rules -> app bundle) · drive_app.py (browser check)
web/             The PWA — Next.js 16 + React 19 + TypeScript, deploys to Vercel
tests/           85 tests, fully offline
data/            raw (immutable) · interim · processed · external
notebooks/       Analysis; logic lives in src/daloy, not in cells
models/          Phase 5-6
```

---

## Two design decisions worth knowing up front

**Spatial units are H3 cells, not barangays.** Cainta has seven barangays. Seven
observations cannot support supervised learning, so every spatial feature lives on an
H3 r9 cell (~0.1 km², roughly 430 over Cainta). This also happens to be the privacy
answer: `daloy.spatial.bin_point` is the only function that should ever see a precise
coordinate, and it does not return one.

**The taxonomy is keyed to junkshop trade names.** `bote`, `sibak`, `tanso`, `karton` —
not academic categories. TrashNet's six classes are useless at a Cainta junkshop
counter.

---

## The sachet problem

`plastic_film_sachet` has no resale value, no junkshop buyer, is the dominant residual
in Philippine household waste, and is the primary creek-clogging material. It is also
barely represented in TACO or TrashNet.

**The model will be most confidently wrong about the object that matters most.**

This is not a bug to patch later — it is why the school partnership exists, and why
`daloy.metrics.evaluation_report` breaks sachet recall out separately and refuses to
let it hide inside a headline accuracy figure.

---

## Governance

Non-negotiables, enforced in `scrapers/common.py` rather than left to memory:

- robots.txt checked per host; a disallowed URL raises rather than fetches
- ≥2s between requests; User-Agent names the project and a contact address
- content-hash caching — an unchanged government PDF is downloaded once
- **Facebook is on a denylist and raises.** Meta's ToS forbids it, and it would poison
  credibility with the LGU
- every fetch appends provenance to `data/raw/_manifest.jsonl`

Privacy (RA 10173 and Cainta Ordinance 2023-005): geotags are personal data. Store cell
IDs, never raw coordinates. Students are minors — school-mediated consent, no public
profiles, class-level aggregates only. See
[docs/privacy_notice_tl.md](docs/privacy_notice_tl.md).

---

## Attribution

- **TACO** (Proença & Simões, 2020) — CC BY 4.0
- **TrashNet** (Yang et al., Stanford, 2016)
- **OpenStreetMap** contributors — ODbL. The junkshop field survey gets contributed back.
- **PSA**, **DENR-EMB**, **NSWMC**, **COA** — public documents, cited individually with
  retrieval dates in `data/raw/_manifest.jsonl`

---

## Open questions

Three the plan does not answer, from §11. They should be settled before Phase 3:

1. **What makes a resident open this a second time?** The Pathway Card is a one-time
   revelation. Junkshop prices are the only genuinely dynamic content.
2. **Will junkshops publish prices?** Opacity may be their margin. The field survey
   form front-loads a five-shop test for exactly this.
3. **Does the LGU want this to exist?** A public map of leakage hotspots is also a
   public map of a municipality's failures. Find out before building the heatmap.
