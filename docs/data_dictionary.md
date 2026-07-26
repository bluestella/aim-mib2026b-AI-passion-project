# Data Dictionary

Field-level reference for every table in the DALOY Scan pipeline. Derived from plan
§4.2 and cross-checked against the LGU-SWM-SCMAR reporting form, which defines what a
Philippine LGU is legally required to hold (plan §3, Tier 2.1).

**Availability** is stated for each field, because most of this does not exist yet:

| Marker | Meaning |
|---|---|
| `now` | Available today from a public source |
| `P1`–`P4` | Arrives in that phase of the roadmap (plan §9) |
| `FOI` | Depends on a Freedom of Information response — may never arrive |

---

## `materials` — the taxonomy

Source: `rules/cainta_disposal_rules.yaml`. Eleven classes (ten plus a residual
catch-all), keyed to junkshop trade names rather than academic categories, because
TrashNet's six classes are useless at a Cainta junkshop counter (plan §5.1).

| Field | Type | Availability | Notes |
|---|---|---|---|
| `class` | string, PK | now | One of the 11 classes. The Stage-1 target variable. |
| `local_names` | string[] | now | Trade names: bote, sibak, tanso, karton. Drives the manual picker in the rules-only v1. |
| `resin_code` | int 1–7, nullable | now | Plastics only. Null for metals, glass, paper, organics. |
| `is_laminated_multilayer` | bool | now | True only for sachet. The single most consequential flag in the table. |
| `typical_unit_mass_g` | float | now (estimate) | For the "Bote Bank" ledger. Estimates until weighed. |
| `contamination_sensitivity` | enum low/medium/high | now | High = a food-soiled item is refused at the counter and downgrades a whole bale. |
| `epr_covered` | bool | now | RA 11898 plastic packaging coverage. |
| `pathway` | FK → pathways | now | The Stage-2 output. |
| `fallback_pathway` | FK → pathways, nullable | now | Used when the primary route is unavailable locally. |
| `price_php_per_kg` | {low, high, confidence, as_of} | P2 | Indicative ranges until the field survey lands. |
| `accepted_by_pct_of_local_junkshops` | float 0–1, nullable | P2 | Null everywhere except sachet/organics, where it is a known 0. |
| `is_critical_class` | bool | now | Sachet only. Forces separate recall reporting (plan §10). |

## `pathways`

| Field | Type | Notes |
|---|---|---|
| `id` | string, PK | `sell_junkshop`, `barangay_mrf`, `home_compost`, `special_waste_dropoff`, `residual_to_slf` |
| `label_en`, `label_tl` | string | Both required. The app is bilingual by default, not by toggle. |
| `terminus` | enum | `recovery` / `controlled` / `disposal`. Drives the Flow Simulation branch. |

## `legal_sources`

| Field | Type | Availability | Notes |
|---|---|---|---|
| `id` | string, PK | now | e.g. `ord-2023-012` |
| `citation` | string | now | Full formal citation, as it would appear in a footnote. |
| `verification` | enum | P1 | `unverified` → `harvested`. **Nothing may be attributed to the municipality while this is `unverified`** (plan §7.8). |
| `retrieved_on` | date, nullable | P1 | Date the PDF was actually downloaded. |
| `local_path` | path, nullable | P1 | Points into `data/raw/cainta_ordinances/`. |

---

## `junkshops` — the moat

Source: OSM seed (`scrapers/osm_overpass.py`) plus primary field survey. Nothing else
in the plan is as valuable per hour spent (plan §3, Tier 4.4).

| Field | Type | Availability | Notes |
|---|---|---|---|
| `shop_id` | string, PK | P2 | |
| `name` | string | P2 | |
| `lat`, `lon` | float | P2 | **Business premises, not personal data.** Distinct from user geotags — see privacy notice. |
| `h3_r9` | string | P2 | Spatial join key. |
| `accepted_materials` | string[] → materials.class | P2 | The field survey's core question. |
| `price_php_per_kg` | float | P2 | Per material. Observed at the counter, not an index price. |
| `price_updated_at` | date | P2 | **Must be shown in the UI.** Confidence decays visibly with age (plan §10). |
| `min_weight_kg` | float, nullable | P2 | Many shops refuse below a threshold. |
| `open_hours` | string | P2 | OSM opening_hours syntax. |
| `accepts_walk_in` | bool | P2 | Some buy only from collectors, not residents. A shop that refuses walk-ins is useless to this app. |
| `last_verified_date` | date | P2 | Distinct from `price_updated_at`: the shop may still exist while its prices are stale. |
| `osm_id` | string, nullable | P2 | Set once the survey is contributed back to OSM under ODbL. |

## `commodity_prices` — the lag features

Source: `scrapers/scrap_prices.py`. Tidy long format, one row per material per day.

| Field | Type | Notes |
|---|---|---|
| `observed_on` | date | |
| `material` | FK → materials.class | Synonyms are mapped at ingest, so the join is unambiguous. |
| `price_php_per_kg` | float | **Commodity index, not a counter price.** Never displayed to users as what a shop pays. |
| `source` | string | URL or "manual entry". |
| `method` | enum scraped/manual | Manual entry exists so the series stays continuous when a layout change breaks the parser. |

Derived at model time: `aluminium_index_lag7`, `pet_flake_price_lag7`, `steel_index_lag7`.

---

## `spatial_cells` — H3 r9, not barangays

The n=7 problem (plan §1). Seven barangays cannot support supervised learning, so every
spatial feature lives on an H3 resolution-9 cell (~0.1 km², roughly 430 over Cainta).
Barangay codes remain a labelling and join key only.

| Field | Type | Availability | Notes |
|---|---|---|---|
| `h3_r9` | string, PK | now | From `daloy.spatial.bin_point`. |
| `barangay_psgc` | string | now | Join key to LGU records. **Not a modelling unit.** |
| `population_density` | float | now | POPCEN 2024 disaggregated by cell area. Disaggregation is an assumption, not a measurement — record it as such. |
| `household_count` | int | now | |
| `built_up_ratio` | float 0–1 | P2 | From OSM landuse. |
| `distance_to_nearest_waterway_m` | float | now | OSM waterway network. |
| `elevation_m`, `slope` | float | P2 | Needed for the Flow Simulation's downhill traversal. |
| `distance_to_nearest_MRF_m` | float | FOI / P2 | |
| `junkshop_density_per_km2` | float | P2 | |
| `road_length_km` | float | now | OSM. |
| `school_count`, `marketplace_count` | int | now | OSM institutional anchors. |
| `historical_flood_flag` | bool | P1 | Typhoon Carina (2024), STS Crising (2025). Needs a citable source before it appears in the UI. |
| `user_report_count_30d` | int | P3 | Generated by the app itself. |

## `scans` — what the app generates

This is the v2 training set (plan §2.1). It is also the table most exposed to RA 10173,
so its schema is a privacy decision as much as a modelling one.

| Field | Type | Notes |
|---|---|---|
| `scan_id` | uuid, PK | |
| `h3_r9` | string | **Never a raw lat/lon.** Binned at the request handler; the coordinate is not persisted (plan §7.5). |
| `predicted_class` | FK → materials.class | |
| `confidence` | float 0–1 | Calibrated. Drives the confidence gate. |
| `confirmed_class` | FK → materials.class, nullable | User correction. The highest-value column in the table — it labels exactly where the model is weak (plan §6.2). |
| `image_ref` | string, nullable | Only where consent covers image retention. |
| `role` | enum resident/teacher/student | |
| `class_group_id` | string, nullable | Student scans aggregate to a class, never to a named child (plan §7.6). |
| `created_at` | timestamp | Truncate to the hour. A precise timestamp plus a cell is close to re-identifying. |

## `users` — privacy-bounded

| Field | Type | Notes |
|---|---|---|
| `user_id` | uuid, PK | Pseudonymous. No name, no email required for the resident flow. |
| `role` | enum | |
| `coarse_barangay` | string | **Barangay-level at most. Never a precise home location.** |
| `scan_count`, `streak_days` | int | |
| `correction_rate` | float | How often this user overrides the model — a data-quality weight, and a signal worth watching for a user who is systematically mislabelling. |

**Not collected:** precise home coordinates, real names for student accounts, contact
details for minors, device identifiers beyond a session token.

---

## Provenance

Every fetched file appends a row to `data/raw/_manifest.jsonl`:

| Field | Notes |
|---|---|
| `source_id` | Which scraper fetched it |
| `url` | Where it came from |
| `path` | Where it landed |
| `sha256` | Content hash — detects a silently revised government PDF |
| `fetched_at` | ISO 8601 UTC |

This is what makes plan §7.8 enforceable: any figure that reaches a slide can be traced
to a URL and a date. If the MENRO later disputes a number, the answer is an audit
trail, not an argument.
