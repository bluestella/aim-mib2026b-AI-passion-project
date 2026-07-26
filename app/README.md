# app/ — the PWA

**Phase 3. Not started.**

A mobile-first Progressive Web App — no install, phone camera only. Plan §9 ships this
with **zero machine learning**: a manual material picker instead of a classifier, plus
the Pathway Card and the Flow Simulation.

That sequencing is deliberate. If Phases 4–6 never happen, Cainta still gets the first
machine-readable map of where its waste actually goes.

## What v1 needs

1. **Material picker** — the 11 classes by trade name (`bote`, `sibak`, `tanso`).
   `daloy.rules_engine.find_by_local_name` already resolves these.
2. **Pathway Card** — the Stage-2 payload. `format_pathway_card` renders the same
   fields as plain text today, so the rules can be demonstrated before any UI exists.
3. **Flow Simulation** — a ~10s animated trace along OSM `waterway` polylines,
   terminating at Laguna de Bay or at a recovery node. A deterministic graph traversal
   over pre-computed geometry, not a simulation model.
4. **Junkshop map** — from the Phase-2 field survey, with `last_verified_date` visible.

## Two things the UI must enforce

**Never present unverified rules as official.** Gate on
`Pathway.is_presentable_as_official`. While it returns `False`, the app may show the
guidance but must not attribute it to the municipality (plan §7.8). It returns `False`
for every material today.

**Bin the location before it leaves the request handler.** Call
`daloy.spatial.bin_point` on arrival and never persist the coordinate. The cell is what
gets stored (plan §7.5).

## Later

- v2 adds on-device classification via TF.js or ONNX Runtime Web, with the confidence
  gate from plan §6.2: below threshold, show the top-3 and let the user pick. Every such
  interaction is a labelled sample from exactly where the model is weak.
- Target: **< 1.5s inference on a mid-range Android**.

## Before a single student uses this

Parental consent flow, school-mediated. No public profiles for minors. Class-level
leaderboards only — never individual children. See
[../docs/privacy_notice_tl.md](../docs/privacy_notice_tl.md), which still needs legal
review.
