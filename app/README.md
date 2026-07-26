# app/ — the PWA

**Phase 3: rules-only v1. Built.**

A mobile-first Progressive Web App — no install, no camera, **no machine learning**.
The user picks a material by its junkshop trade name and gets the Pathway Card plus
the Flow Simulation.

That sequencing is deliberate (plan §9). If Phases 4–6 never happen, Cainta still gets
the first machine-readable map of where its waste actually goes.

## Run it

```bash
python scripts/build_app_data.py          # compile rules/*.yaml -> app/data/rules.json
python -m http.server 8765 --directory app
# open http://127.0.0.1:8765/
```

It must be served over HTTP. Opening `index.html` as a `file://` URL fails, because
the browser will not `fetch()` the data bundle from the filesystem — the app detects
this and says so rather than showing an empty screen.

## Verify it

```bash
pip install -e ".[browser]"
python scripts/drive_app.py --screenshots ./shots
```

This drives all ten screens in Chromium and asserts the invariants below. It found two
bugs that unit tests structurally could not: a render that scheduled the flow animation
before a navigation that immediately cancelled it, and a modifier checkbox that reset
while the state behind it persisted.

## What it does

| Screen | Notes |
|---|---|
| Barangay setup | Asked once, stored locally. **This is the entire location model.** |
| Material picker | 11 classes as trade names — `bote`, `sibak`, `tanso`, `karton` |
| Modifiers | Contaminated / battery / e-waste, driven by the overrides in the rules YAML |
| Pathway Card | Verdict, price position, preparation, legal basis |
| Flow Simulation | Staged animated trace: leakage → Laguna de Bay, or recovery → remade |
| Bote Bank | Local ledger; totals **mass, not pesos** |
| Junkshops | Honest empty state — there are zero surveyed shops |
| Privacy | Plain Tagalog, with an English summary |

## Four invariants

These are asserted by `scripts/drive_app.py`, not just intended.

**1. Nothing is attributed to the municipality while unverified.** Every card gates on
`presentable_as_official` from the data bundle. It is `false` for all 11 materials
today, so cards say *"Kaugnay na batas"* (related law) and add an explicit line that
this is not an official statement of the LGU — never *"Batay sa"* (based on). See plan
§7.8.

**2. No location is requested or stored.** There is no geolocation call anywhere in
this app. The barangay picker is the whole location model and never leaves
`localStorage`. Plan §7.5 required binning coordinates before storage; v1 goes further
by never obtaining one.

**3. Prices are never presented as what a shop will pay.** Every price carries the
unverified caveat while `verified_shops` is 0, the Bote Bank deliberately totals grams
rather than pesos, and glass — which carries a nominal price but is usually refused —
shows *"Madalas tinatanggihan"* instead of a green price tag.

**4. The flow diagram is labelled schematic.** It is a staged diagram of the documented
drainage direction, never drawn over a basemap, because a stylised line on a map reads
as surveyed truth. No creek is named, because which creek serves which barangay is
unverified.

## Design decisions worth knowing

**Vanilla JS, not React.** Plan §8 specifies "React + TF.js/ONNX". That stack is for the
v2 classifier; v1 has no ML, no routing and no shared state worth a framework, so it
ships as a static PWA with no build step and no dependencies. React comes back with
TF.js in Phase 6 — this is a deferral, not a rejection.

**Barangay picker instead of GPS.** The plan assumed a geotag binned to an H3 cell.
Without junkshop locations there is nothing to compute a distance *to*, so v1 asks for
a barangay instead and never triggers a location permission prompt. When Phase 2 lands
shop coordinates, distance sorting goes through `daloy.spatial.bin_point` and the
coordinate is still never persisted.

**Rules are compiled, not duplicated.** `scripts/build_app_data.py` flattens the YAML
into `app/data/rules.json`; the browser never re-implements resolution logic beyond
override matching, which is kept in the same order as the Python so both answer
identically. `tests/test_build_app_data.py` fails if the committed bundle drifts.

**Offline-first.** `sw.js` precaches everything. The rules bundle is network-first so a
rebuild is picked up as soon as there is signal; everything else is cache-first. Bump
`CACHE` in `sw.js` when the app changes — a stale cached bundle would show outdated
pathways.

## What v1 does not do

- **No camera, no classifier.** That is Phases 4–6.
- **No junkshop locations.** Phase 2 fieldwork; the screen says so plainly rather than
  showing an empty map that implies Cainta has no junkshops.
- **No collection schedules.** Blocked on FOI request C — and per plan §11 this is
  probably the strongest recurring-value feature the app could carry.
- **No accounts, no backend, no student features.** The school channel needs
  school-mediated parental consent and legal review before a single minor uses this.

## Before a student uses this

Parental consent flow, school-mediated. No public profiles for minors. Class-level
leaderboards only — never individual children. See
[../docs/privacy_notice_tl.md](../docs/privacy_notice_tl.md), which still needs legal
review.
