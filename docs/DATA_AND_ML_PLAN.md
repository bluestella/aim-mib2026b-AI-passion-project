# Project DALOY Scan — Data & Machine Learning Plan

**A zero-waste web application for Cainta, Rizal**

| | |
|---|---|
| **Prepared for** | Seph Rannie M. Buluran |
| **Date** | 26 July 2026 |
| **Status** | Pre-build planning document — v1.0 |
| **Decision context** | Real deployable civic app · residents + teachers + students · photo classification core · cold-start accepted (ML in v2) · ambitious core, but every data source must be real today |

---

## 0. Executive Summary (read this if you read nothing else)

**The concept:** *"Saan Napupunta?"* — a mobile-first web app where a resident, teacher, or student photographs a piece of waste and immediately sees **the two futures of that object in Cainta specifically**: the leakage path (their street → barangay drainage → creek → Manggahan Floodway → Laguna de Bay, overlaid on Cainta's own flood history) and the recovery path (nearest junkshop or MRF, current ₱/kg, next barangay pickup, and the EPR recovery target it counts toward).

**Why this works and a generic trash classifier doesn't:** Stage 1 (what material is this?) is a commodity — TACO and TrashNet solve it and anyone can ship it. Stage 2 (where does *this* material go in *this* municipality, who buys it, for how much) has never been assembled for Cainta. **Stage 2 is the moat.** It is also the literal question Project DALOY's own founding post asks: *"Saan napupunta ang basura natin?"*

**The single biggest technical risk:** open waste datasets have almost no **sachet / laminated multilayer** class — which is the dominant residual waste stream in Philippine households. The model will be most confidently wrong about the most important local object. This is not a bug to patch later; it is the reason the school partnership exists.

**The single biggest data reality:** there is no downloadable Cainta waste dataset. Everything Cainta-specific must come from (a) scraping the LGU's own published PDFs, (b) a **Freedom of Information request** under EO 2 s. 2016 — which requires no warm door and is a legal right, and (c) data the app itself generates.

---

## 1. Reality Check — What Exists, What Doesn't

Before any scraper is written, be honest about the data landscape.

| Layer | Availability | Implication |
|---|---|---|
| National solid waste statistics (generation rates, MRF/SLF counts, diversion) | **Public**, but in PDF reports, not APIs | Parse-able; use as priors and denominators, not training rows |
| LGU-level SWM reporting schema (SCMAR) | **Public template**, actual filled data not published | Template = your feature dictionary. Filled data = FOI request |
| Cainta ordinances & environment code | **Public**, static PDFs on a Wix site | Directly scrapeable. Highest-value local source |
| Cainta 10-Year SWM Plan | **Not confirmed public** | FOI to NSWMC and/or Cainta MENRO |
| Barangay-level waste tonnage, Cainta | **Almost certainly not published** | FOI; assume you may not get it |
| Junkshop locations & prices, Cainta | **Not published anywhere** | OSM baseline + primary field collection. This is your moat |
| Waste images, Philippine context | **Effectively absent** | TACO/TrashNet transfer + primary collection |
| EPR obliged-enterprise registry | **Portal exists** (epr.emb.gov.ph) | Brand-level linkage; check ToS before scraping |

### The n=7 problem

Cainta has **seven barangays**: San Andres, San Isidro, San Juan, San Roque, Santa Rosa, Santo Domingo, Santo Niño *(verify against PSGC 0405805000 before hardcoding — PSA issues quarterly PSGC corrections)*.

Seven observations cannot support supervised learning at the barangay level. Any spatial modelling must operate on a finer unit:

- **H3 hexagonal cells** at resolution 9 (~0.1 km²) → ~430 cells over Cainta's 42.99 km²
- or **subdivision / purok** polygons digitised from OSM
- or **drainage catchment segments** derived from OSM `waterway` + elevation

Design for this from day one. Do not build a barangay-keyed schema you'll have to tear out.

---

## 2. The Application Concept

### 2.1 Core loop

```
SCAN → CLASSIFY → PATHWAY CARD → ACTION → LOG → STREAK/LEADERBOARD
```

1. **Scan.** User photographs an item (phone camera, no app install — PWA).
2. **Classify.** Stage-1 model returns material class + confidence.
3. **Pathway Card.** The payload that makes this Cainta-specific:
   - `Ito ay: PET bottle (bote)`
   - `Kung itatapon: Barangay San Juan drainage → Sapang Cainta → Manggahan Floodway → Laguna de Bay. Your barangay flooded in Typhoon Carina (2024) and STS Crising (2025).`
   - `Kung ire-recycle: Junkshop [name], 400m. Kasalukuyang presyo: ₱10–14/kg.`
   - `Next segregated pickup sa inyo: [day]`
   - `Ordinance: Cainta Ord. 2022-010 requires segregation at source.`
4. **Action.** Save to "Bote Bank" ledger, get directions, or share.
5. **Log.** Every scan is a labelled datapoint with geotag + user confirmation. **This is the v2 training set.**

### 2.2 The "wild but feasible" mechanic — Flow Simulation

Instead of a static label, the app plays a ~10-second animated trace of the item moving through Cainta's actual drainage network (OSM `waterway=drain/stream` polylines + elevation), terminating either at Laguna de Bay or at a recovery node. Two paths, side by side.

Feasible because it is a **deterministic graph traversal over pre-computed geometry**, not a simulation model. The ML is only the entry point (what material?). The emotional payload comes from real local geography and Cainta's real flood record.

### 2.3 Roles

| User | Primary value | Data they generate |
|---|---|---|
| **Resident** | Where do I take this, what's it worth, when's pickup | Scans, geotags, corrections |
| **Teacher** | Ready-made lesson + class dashboard + verified impact report | Curated, verified label batches |
| **Student** | Streaks, class-vs-class leaderboard, "Sachet Hunter" badge | High-volume labelled images — the sachet corpus |
| *(v2)* Junkshop | Free listing, inbound supply | Price updates, acceptance rules |
| *(v2)* MENRO | Heatmap of leakage reports | Validation signal |

**The teacher/student channel is not a nice-to-have.** It is your annotation workforce and it solves the cold-start problem you accepted. A single Grade 9 science class doing one "sachet audit" assignment produces ~1,000 labelled Philippine-context images.

---

## 3. Data Sources to Scrape

Grouped by tier. Every entry below is a source verified to exist as of July 2026.

### Tier 1 — Cainta-specific (highest value, lowest volume)

| # | Source | URL / Access | Format | Cadence | What you extract |
|---|---|---|---|---|---|
| 1.1 | Cainta Resolutions & Ordinances | `cainta.gov.ph/resolutionsandordinances` | Wix HTML → PDF links at `/_files/ugd/{hash}.pdf` | Monthly | Ord. 2016-013 & 2022-010 (segregation at source), 2022-002 (anti-littering), **2023-012 Environmental Protection and Waste Management Code of 2023**, 2023-005 (Data Privacy Act operationalisation) |
| 1.2 | Cainta Barangays | `cainta.gov.ph/barangays` | HTML | Quarterly | Barangay names, officials, contact points |
| 1.3 | Cainta Departments & Offices | `cainta.gov.ph/departments-and-offices` | HTML | Quarterly | **MENRO** identity + contact — your cold-outreach target |
| 1.4 | Cainta Full Disclosure | `cainta.gov.ph/fulldisclosure` | PDF | Quarterly | SRE / budget line items for solid waste; procurement of hauling contracts |
| 1.5 | Sangguniang Bayan legislation archive | `sbonecaintalegislation.wordpress.com` | HTML/WordPress | Monthly | Older ordinances not on the main site (e.g. 2012 plastic bag & styrofoam ban) |
| 1.6 | One Cainta official Facebook page | `facebook.com/onecainta.onecainta` | — | — | **Do not scrape.** Violates Meta ToS. Request an export via MENRO, or manual capture with admin consent |

> **Scraping note for 1.1–1.4:** Cainta's site is Wix-generated. Asset PDFs sit at stable hashed paths under `/_files/ugd/`. Scrape the index page for `<a href>` matching `_files/ugd/.*\.pdf`, then fetch. Content is text-layer PDF (not scanned) in most cases — `pdfplumber` will work; keep `pytesseract` as fallback.

### Tier 2 — National government (structure, priors, denominators)

| # | Source | URL / Access | Format | What you extract |
|---|---|---|---|---|
| 2.1 | **LGU-SWM-SCMAR reporting form** | `nswmc.emb.gov.ph/wp-content/uploads/2016/09/LGU-SWM-SCMAR-revised-March-2016.pdf` | PDF | **The canonical LGU SWM data schema.** Tables cover: BSWMC status per barangay, % compliance to segregation-at-source & segregated collection, households served, mixed-waste collection volumes, MRF locations & wastes processed, MRS data. **Use this as your feature dictionary — it tells you exactly what fields a Philippine LGU is legally required to hold.** |
| 2.2 | National Solid Waste Management Status Report | `nswmc.emb.gov.ph/wp-content/uploads/2016/06/Solid-Wastefinaldraft-12.29.15.pdf` and `eeid.emb.gov.ph/.../SOLIDWASTE-LAYOUT_final.pdf` | PDF | MSW composition %, per-capita generation rates (national avg ~0.40 kg/day; Metro Manila higher), MRF counts by region, projected generation |
| 2.3 | NSWMC sanitary landfill inventory | `nswmc.emb.gov.ph/wp-content/uploads/2021/06/landfills-may2021.pdf` | PDF table | SLF locations, operators, LGUs served — includes Rizal facilities |
| 2.4 | RA 9003 IRR | `nswmc.emb.gov.ph/wp-content/uploads/2025/04/RA-9003-IRR.pdf` | PDF | Legal definitions for your taxonomy; BSWMC composition; MRF requirements |
| 2.5 | SWM Plan Formulation Guidebook | `nswmc.emb.gov.ph/wp-content/uploads/2017/09/FSWMP-Proof-Layout.pdf` | PDF | Collection route / service-area structure, "no segregation no collection" policy patterns |
| 2.6 | **eFOI portal** | `foi.gov.ph/agencies/nswmc/` | Web form | **See §3.1 below. This is your no-warm-door workaround.** |
| 2.7 | EPR registry portal | `epr.emb.gov.ph` | Web portal | Obliged-enterprise registrations. **Check ToS/robots.txt before automated access** — prefer FOI for the register |
| 2.8 | COA Performance Audit, SWM Program | `coa.gov.ph/reports/performance-audit-reports/2023-2/solid-waste-management-program/` | HTML/PDF | Independent audited MRF/SLF counts and diversion failures — excellent for grounding claims |
| 2.9 | PSA PSGC — Cainta | `psa.gov.ph/classification/psgc/barangays/0405805000` | HTML | Canonical barangay codes. Watch quarterly PSGC updates |
| 2.10 | PSA 2024 POPCEN | `psa.gov.ph` | XLSX/PDF | Cainta: 386,321 pop, 90,707 households, 42.99 km². Barangay-level counts |
| 2.11 | PSA FIES public-use file | `psa.gov.ph` (request/download) | CSV/SAV | Household income deciles & expenditure by region — the standard covariate for waste generation rate |
| 2.12 | DENR-EMB CALABARZON (Region IV-A) | `r4a.denr.gov.ph` / EMB regional site | HTML/PDF | Regional SWM bulletins, LGU compliance status |
| 2.13 | LLDA | `llda.gov.ph` | HTML/PDF | Laguna de Bay water quality stations; Cainta discharges into the LLDA basin — this is the terminus of your Flow Simulation |
| 2.14 | PAGASA | `pagasa.dost.gov.ph` | HTML/API | Rainfall for the leakage-risk feature (waste mobilises during storms) |

> **On DA (Department of Agriculture):** be honest — DA is *peripheral* to a municipal waste app. It becomes relevant only for the biodegradable stream: DA-BSWM and PhilRice composting guidance, and the PNS for organic fertiliser (relevant if you route food waste to vermicomposting). Don't inflate it into a pillar. One scraper, low priority.

### Tier 3 — Open datasets (Stage-1 model training)

| # | Dataset | Access | License | Size | Note |
|---|---|---|---|---|---|
| 3.1 | **TACO** (Trash Annotations in Context) | `tacodataset.org` / arXiv 2003.06975 / Roboflow mirrors | **CC BY 4.0** | ~1,500 images, ~4,784 annotations, 28–60 classes | Litter *in the wild* — closest to real Cainta conditions. Class-imbalanced |
| 3.2 | **TrashNet** (Stanford, Yang et al. 2016) | GitHub | Open | 2,527 images, 6 classes | Clean white background — good for pretraining, poor for deployment realism |
| 3.3 | **OpenLitterMap** | `openlittermap.com` | Open (check per-image) | ~100k+ geotagged user photos | Geotagged, but **Europe-dominated** and inconsistently annotated |
| 3.4 | AquaTrash | GitHub (TACO derivative) | Open | 369 images | Water-borne litter — thematically perfect for the creek narrative |
| 3.5 | GINI / WADE-AI | GitHub | Open | ~1,400 / Street View | Single-class litter presence — useful for a "is there litter here?" detector |

### Tier 4 — Local market & geography (the moat)

| # | Source | Access | What you extract |
|---|---|---|---|
| 4.1 | **OpenStreetMap Overpass API** | `overpass-api.de/api/interpreter` | Junkshops, MRFs, drainage network — **see §3.2 for the query** |
| 4.2 | scrap.trade Philippines | `scrap.trade/scrap-prices/philippines/` | Daily copper / steel / aluminium ₱/kg — the upstream driver of junkshop bid prices |
| 4.3 | LME / commodity indices | Public quotes | Lag-feature for the price regression |
| 4.4 | **Primary field survey** | Your own | Junkshop name, coords, hours, accepted materials, ₱/kg by material, min. weight. **~30–60 shops. Two weekends of fieldwork. Nothing else in this plan is as valuable per hour spent.** |

---

### 3.1 The FOI Play — your answer to "no warm door"

You said you have no warm contact at Cainta MENRO. You don't need one.

Under **Executive Order No. 2, s. 2016**, any Filipino can request records from executive-branch agencies through `foi.gov.ph`. NSWMC is a listed agency with an active request queue — waste-data requests for theses and feasibility studies are routine and get answered.

**File three requests in week 1:**

| Request | Agency | Ask for |
|---|---|---|
| A | NSWMC (via eFOI) | Cainta's most recent **LGU-SWM SCMAR** submission and approved **10-Year SWM Plan**, CY 2020–2025 |
| B | DENR-EMB Region IV-A (CALABARZON) | MRF inventory and barangay-level compliance status for Cainta, Rizal |
| C | Cainta MENRO (paper/email FOI — LGUs under their own FOI ordinance) | Collection routes & schedules by barangay; hauling contract volumes; MRF locations |

Set a realistic expectation: **file all three, budget 15–30 working days, assume a ~50% substantive hit rate.** Even one partial response transforms this project. And the FOI paper trail *itself* is the credential that opens the MENRO door for the real partnership conversation. A citizen with a filed request and a working prototype is a very different visitor than a citizen with a pitch deck.

### 3.2 Overpass query for Cainta

Cainta bounding box (approx): `14.545, 121.085, 14.620, 121.145` — **tighten against the official PSGC boundary before production.**

```
[out:json][timeout:60];
(
  // Recovery nodes
  nwr["amenity"="recycling"](14.545,121.085,14.620,121.145);
  nwr["shop"="scrap_yard"](14.545,121.085,14.620,121.145);
  nwr["amenity"="waste_transfer_station"](14.545,121.085,14.620,121.145);
  nwr["amenity"="waste_disposal"](14.545,121.085,14.620,121.145);
  nwr["landuse"="landfill"](14.545,121.085,14.620,121.145);

  // Leakage network — the Flow Simulation geometry
  way["waterway"~"stream|drain|ditch|river|canal"](14.545,121.085,14.620,121.145);

  // Institutional anchors
  nwr["amenity"="school"](14.545,121.085,14.620,121.145);
  nwr["amenity"="marketplace"](14.545,121.085,14.620,121.145);
);
out center tags;
```

**Expect this to return very little.** Philippine junkshops are systematically under-mapped, and OSM tagging for scrap yards is inconsistent (`amenity=recycling` + `recycling:scrap_metal=yes` is the dominant convention; `shop=scrap_yard` is rare). Treat OSM as a **seed, not a source** — then contribute your field survey back to OSM. That is both good citizenship and free permanent hosting for your moat.

---

## 4. Feature Engineering

### 4.1 Stage-1 features — image → material class

Raw pixels do not feed a kNN. Build a feature vector, then run your classical models on it. Three tiers, and you should compute all three so you can compare:

| Tier | Features | Dim | Purpose |
|---|---|---|---|
| **A. Hand-crafted** | HSV colour histogram (32 bins × 3), HOG (9 orientations, 8×8 cells), LBP texture, Hu moments, aspect ratio, edge density, mean specular highlight ratio | ~250 | Fully interpretable; defensible in a methods section; fast on-device |
| **B. Transfer embeddings** | Penultimate-layer output of a frozen ImageNet-pretrained **MobileNetV3-Small** (576-d) or **EfficientNet-B0** (1280-d) | 576–1280 | The workhorse. Deployable in-browser via TF.js / ONNX Runtime Web |
| **C. Reduced** | PCA on Tier B, retaining 95% variance (~60–120 components) | ~100 | **Mandatory before kNN.** Distance metrics degenerate in 1280-d — this is the classic curse-of-dimensionality trap |

Augmentation, tuned to Philippine deployment conditions: random rotation ±25°, brightness/contrast jitter (sari-sari store fluorescent light vs. midday tropical sun), motion blur, JPEG compression artefacts (low-end Android cameras), partial occlusion, wet/muddy overlay.

### 4.2 Stage-2 features — the local knowledge graph

**Per material class:**
`material_class`, `resin_code` (1–7), `is_laminated_multilayer`, `typical_unit_mass_g`, `contamination_sensitivity`, `bulk_density`, `accepted_by_pct_of_local_junkshops`, `epr_covered_flag` (RA 11898 plastic packaging)

**Per junkshop node:**
`lat`, `lon`, `h3_r9`, `distance_to_user_m`, `accepted_materials[]`, `price_php_per_kg`, `price_updated_at`, `min_weight_kg`, `open_hours`, `accepts_walk_in`, `last_verified_date`

**Per spatial cell (H3 r9 — NOT barangay):**
`population_density` (POPCEN disaggregated by cell area), `household_count`, `built_up_ratio`, `distance_to_nearest_waterway_m`, `elevation_m`, `slope`, `distance_to_nearest_MRF_m`, `junkshop_density_per_km2`, `road_length_km`, `school_count`, `marketplace_count`, `historical_flood_flag`, `user_report_count_30d`

**Per market/time:**
`aluminium_index_lag7`, `pet_flake_price_lag7`, `steel_index_lag7`, `month`, `is_ber_month` (Sept–Dec consumption spike), `days_since_typhoon`, `rainfall_7d_mm`

**Per user/session (privacy-bounded — see §7):**
`scan_count`, `streak_days`, `correction_rate`, `role` (resident/teacher/student), `coarse_barangay` — **never precise home coordinates.**

---

## 5. Target Variables — Recommendation

### 5.1 Primary target (build this)

**`material_class`** — multiclass, 10 classes, deliberately mapped to **junkshop trade names**, not to academic taxonomy. This is the single most important design decision in this document: TrashNet's six classes are useless at a Cainta junkshop counter.

| Class | Local trade name | Est. ₱/kg (2026, verify) |
|---|---|---|
| `PET_bottle` | bote / plastik | ~10–14 |
| `HDPE_PP_rigid` | sibak | ~15 |
| `plastic_film_sachet` | **sachet / laminated** | **~0 — no market** |
| `aluminium_can` | lata / aluminum | ~50–70 |
| `ferrous_metal` | bakal / yero | ~11–14 |
| `copper_wire` | tanso | ~350+ |
| `glass_bottle` | bote (salamin) | low, often refused |
| `cardboard` | karton | ~4–6 |
| `paper_newsprint` | dyaryo / puting papel | ~4–8 |
| `organic_food_waste` | bulok | compost route |
| *(residual catch-all)* | `residual_other` | — |

> **Why `plastic_film_sachet` is the most important class in the table.** It has no resale value, no junkshop buyer, is excluded from most recycling streams, and is the dominant residual in Philippine household waste — and it's the primary creek-clogging material. It is also barely represented in TACO or TrashNet. Your model will be *most confidently wrong* about the item that matters most. Plan for a dedicated Cainta sachet collection campaign, and report per-class recall on it separately from headline accuracy.

### 5.2 The decision layer — `disposal_pathway`

**Be intellectually honest here:** `disposal_pathway` ∈ {Sell to junkshop, Barangay MRF, Home compost, Special waste drop-off, Residual to SLF} is what the user actually needs — but given `material_class` plus local rules, it is **largely deterministic**. Implement it as a **rules engine keyed to Cainta Ord. 2023-012 and 2022-010**, not as a second classifier.

Do not dress a lookup table up as machine learning. A panel will catch it, and an LGU partner will trust you less when they find out.

### 5.3 Secondary targets (v2, once data accumulates)

| Target | Type | Models | Feasible when |
|---|---|---|---|
| `price_php_per_kg` | Regression | **Lasso** (for feature selection over the commodity-index lags), Ridge, **Gradient Boosting / XGBoost** | After ~30 junkshops × ~12 weeks of price observations (~360 rows) |
| `junkshop_accepts` | Binary classification | Logistic regression, Random Forest | After field survey |
| `cell_leakage_risk` | Binary / ordinal on H3 cells | Gradient Boosting, spatial CV | After ~500+ geotagged user reports |
| `scan_to_action_conversion` | Binary | Logistic regression | The product metric that actually matters |

### 5.4 Baselines — do this before any modelling

Compute the **Proportional Chance Criterion**: `PCC = Σ pᵢ²`, and the **1.25 × PCC** practical threshold. With a heavily imbalanced 10-class waste dataset, a naive majority classifier can look respectable. Report accuracy **against PCC**, plus macro-F1 and the per-class confusion matrix. Headline accuracy alone on this problem is close to meaningless.

---

## 6. Modelling Plan

### 6.1 Stage 1 — model bake-off

Run all of these on Tier-A, Tier-B, and Tier-C feature sets. The comparison *is* the methodological contribution.

| Model | Why it's in the bake-off | Watch out for |
|---|---|---|
| **kNN** (k = 3, 5, 9; Euclidean & cosine) | Interpretable, zero-training, natural fit for "find similar items already labelled in Cainta" | Requires PCA-reduced features; must scale; slow at inference on large corpora |
| **Multinomial logistic regression** | Calibrated probabilities — you need these for the confidence threshold | Linear boundary in embedding space |
| **Linear / Ridge / Lasso** | Only appropriate for the *regression* targets (§5.3), not for material class | Do not misuse for classification |
| **SVM (RBF)** | Historically strong on TrashNet-scale data | Poor scaling; no native probabilities |
| **Random Forest** | Robust baseline, free feature importances | Large model size for in-browser use |
| **Gradient Boosting / XGBoost / LightGBM** | Usually the tabular winner; will likely top the leaderboard on embeddings | Overfits small data; needs early stopping |
| **Fine-tuned MobileNetV3** | The realistic production model | The "commodity" tier — but it's what actually ships |

**Evaluation protocol:** stratified 5-fold CV; hold out a **Cainta-collected test set that never enters training** (this is the only honest measure of transfer); report accuracy, macro-F1, per-class recall, PCC ratio, and inference latency on a mid-range Android device.

### 6.2 The confidence gate

Below a calibrated confidence threshold, **do not guess** — show the top-3 candidates and ask the user to pick. Every such interaction is a free, high-value labelled sample from exactly the region of feature space where the model is weak. This turns the model's weakness into its data-acquisition engine.

---

## 7. Scraping Governance — Non-Negotiables

1. **robots.txt and ToS first.** Check before every new domain. `epr.emb.gov.ph` and PSA in particular.
2. **Rate limit.** ≥2s between requests; identify your agent honestly:
   `User-Agent: DALOY-Scan-Research/1.0 (zero-waste civic app, Cainta; contact: <email>)`
3. **Cache aggressively.** Government PDFs change annually at most. Hash and skip unchanged files. Never re-scrape what you already have.
4. **Never scrape Facebook.** The Project DALOY group and the One Cainta page are off-limits to automation — it violates Meta's ToS and would poison your credibility with the LGU. Request exports through admins.
5. **RA 10173 (Data Privacy Act).** Cainta has *its own* Ordinance 2023-005 operationalising the DPA. Geotags are personal data. Store H3 cell IDs, not raw coordinates. Publish a plain-Tagalog privacy notice. Get parental consent flows right before a single student uses this.
6. **Minors.** Students are minors. The school channel needs school-mediated consent, no public profiles, no leaderboards that identify individual children — class-level aggregates only.
7. **Attribution.** TACO is CC BY 4.0 — attribute it. OSM is ODbL — attribute it, and contribute your junkshop survey back.
8. **Never present scraped data as official.** Label every LGU-derived figure with its source document and date. If MENRO later disputes a number, you want an audit trail, not an argument.

---

## 8. Repository Structure

```
daloy-scan/
├── scrapers/
│   ├── cainta_ordinances.py       # Wix PDF harvester
│   ├── nswmc_reports.py           # EMB/NSWMC PDF corpus
│   ├── psa_psgc.py                # barangay codes + POPCEN
│   ├── osm_overpass.py            # junkshops, MRFs, waterways
│   ├── scrap_prices.py            # daily commodity prices
│   └── foi_tracker.py             # FOI request status log
├── data/
│   ├── raw/          # immutable; never edit
│   ├── interim/      # parsed PDFs → structured
│   ├── processed/    # model-ready
│   └── external/     # TACO, TrashNet, OpenLitterMap
├── notebooks/
│   ├── 01_pdf_parsing_audit.ipynb
│   ├── 02_feature_extraction.ipynb
│   ├── 03_pcc_baseline.ipynb
│   ├── 04_model_bakeoff.ipynb
│   └── 05_cainta_holdout_eval.ipynb
├── models/
├── app/              # PWA — React + TF.js/ONNX
├── rules/
│   └── cainta_disposal_rules.yaml  # keyed to Ord. 2023-012
└── docs/
    ├── data_dictionary.md
    ├── foi_requests/
    └── privacy_notice_tl.md
```

> **Implementation note (added at scaffold time).** The repository as built follows this layout, with one addition: a `src/daloy/` package holds the logic the notebooks would otherwise inline (rules engine, PCC baseline, spatial helpers) so it is importable and unit-testable. Notebooks call into `src/daloy/`; they do not own logic. See `README.md` for what is built versus deferred by phase.

---

## 9. Phased Roadmap

| Phase | Weeks | Deliverable | Gate to proceed |
|---|---|---|---|
| **0. Legal & FOI** | 1–2 | 3 FOI requests filed; robots.txt audit; privacy notice drafted | Requests acknowledged |
| **1. Scrape & parse** | 2–4 | All Tier-1/2 PDFs harvested; ordinance rules extracted into `cainta_disposal_rules.yaml` | Rules engine answers "where does a PET bottle go in Cainta?" correctly |
| **2. Field survey** | 4–6 | 30–60 junkshops mapped with prices & acceptance rules; contributed to OSM | ≥25 shops verified |
| **3. Rules-only v1 ships** | 6–8 | PWA with manual material picker + Pathway Card + Flow Simulation. **No ML.** | Real Cainta users complete the loop |
| **4. Corpus building** | 8–16 | School partnership live; ≥3,000 Cainta-labelled images, sachet-weighted | Sachet class ≥400 images |
| **5. Model bake-off** | 16–20 | All models compared on 3 feature tiers; Cainta holdout eval | Macro-F1 > 1.25 × PCC on holdout |
| **6. ML v2 ships** | 20–24 | On-device classifier + confidence gate | Latency < 1.5s on mid-range Android |
| **7. LGU handover** | 24+ | MENRO dashboard; data-sharing MOA | — |

**Note that Phase 3 ships a genuinely useful product with zero machine learning.** That is deliberate and it is the correct sequencing given your cold-start answer. If Phases 4–6 never happen, Cainta still gets the first machine-readable map of where its waste actually goes.

---

## 10. Risks & Honest Failure Modes

| Risk | Severity | Mitigation |
|---|---|---|
| **Sachet blind spot** | **Critical** | Dedicated collection campaign; report sachet recall separately; never let headline accuracy hide it |
| FOI requests all return nothing | High | Phases 2–3 don't depend on FOI. Field survey is the real moat |
| Junkshop prices go stale | High | Crowd-sourced updates with `last_verified_date` shown in UI; decay confidence visibly |
| TACO/TrashNet transfer fails on Philippine imagery | High | Cainta holdout set is the *only* honest metric. Expect a large drop from published TACO benchmarks |
| MENRO sees this as a threat, not a tool | Medium | Lead with the FOI paper trail and a working prototype; frame as RA 9003 compliance support, not as an audit of them |
| No sustained user engagement after novelty | **Medium–High** | This is the real product risk, not a data risk. The junkshop price feed is the only durable recurring reason to reopen the app. Weight it accordingly |
| Student data privacy incident | Critical | School-mediated consent; class-level aggregates only; no PII in the corpus; legal review before Phase 4 |
| Only 7 barangays → no spatial ML | Certain | Already designed around: H3 r9 cells |

---

## 11. What I'd Pressure-Test Next

Three questions this plan does not answer, and you should answer before Phase 3:

1. **What is the recurring reason a resident opens this a second time?** The Pathway Card is a one-time revelation. Scanning a PET bottle twice teaches nothing new. Junkshop prices are the only genuinely dynamic content — is a price ticker enough to sustain retention? If not, the whole thing is a beautiful demo.
2. **Is the junkshop network actually willing to publish prices?** Price opacity may be their margin. If they refuse, your moat collapses and you're left with a rules engine. Test this with five shops before committing to the field survey.
3. **Does the LGU want this to exist?** A public map of leakage hotspots is, from one angle, a public map of a municipality's failures. Find that out before you build the heatmap, not after.

---

## Appendix A — Verified Reference Figures (as of July 2026)

| Figure | Value | Source |
|---|---|---|
| Cainta population (2024 POPCEN) | 386,321 | PSA |
| Cainta households (2024) | 90,707 | PSA |
| Cainta land area | 42.99 km² | PSA |
| Cainta barangays | 7 | PSGC 0405805000 |
| Cainta PSGC code | 0405805000 | PSA |
| Philippine per-capita MSW generation | ~0.40 kg/day (national avg; Metro Manila higher) | EMB/NSWMC |
| National MRFs | 12,864 (2025, up from 11,779 in 2022) | DENR-EMB |
| Barangays served by MRFs | 19,464 (49.3% nationwide) | DENR-EMB |
| Sanitary landfills | 343 serving 748 LGUs (2025) | DENR-EMB |
| LGUs with approved 10-Yr SWM Plans | 1,416 of 1,592 (89%) | DENR-EMB, 2025 |
| EPR obliged-enterprise threshold | Total assets > ₱100M | RA 11898 |
| EPR recovery targets | 50% (2025), 60% (2026), 70% (2027), 80% (2028+) | RA 11898 |
| TACO dataset | ~1,500 images, ~4,784 annotations, CC BY 4.0 | Proença & Simões, 2020 |
| TrashNet | 2,527 images, 6 classes | Yang et al., Stanford, 2016 |

*All figures should be re-verified against primary sources before publication. Several are as-of-2025 and may have moved.*
