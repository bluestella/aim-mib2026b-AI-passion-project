"""Compile the rules YAML into the web app's data bundle.

The Next.js app cannot read YAML or import ``daloy.rules_engine``. This script is the
bridge: it flattens ``rules/cainta_disposal_rules.yaml`` and
``rules/cainta_flow_schematic.yaml`` into a single ``web/src/data/rules.json``, which
the app imports at build time — so a missing or malformed bundle is a build failure
rather than a runtime blank screen.

The point of compiling rather than hand-maintaining that JSON is that there is exactly
one source of truth. ``tests/test_build_app_data.py`` fails if the committed bundle
drifts from the YAML, so a rules change that never reaches the app is caught in CI
rather than by a user being told the wrong thing.

Verification state is carried through deliberately. The app gates on
``presentable_as_official`` per material, which is false while any ordinance behind
that material is still ``unverified`` (plan §7.8).

Run:
    python scripts/build_app_data.py
    python scripts/build_app_data.py --check   # fail if the committed bundle is stale
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = REPO_ROOT / "rules" / "cainta_disposal_rules.yaml"
FLOW_PATH = REPO_ROOT / "rules" / "cainta_flow_schematic.yaml"
OUTPUT_PATH = REPO_ROOT / "web" / "src" / "data" / "rules.json"

sys.path.insert(0, str(REPO_ROOT / "src"))

from daloy.rules_engine import RulesEngine  # noqa: E402


def build() -> dict:
    """Flatten the YAML sources into the shape the browser wants.

    Resolution happens here rather than in JavaScript: the engine already knows how
    to apply overrides and propagate verification state, and duplicating that logic
    in the client is how the two would drift apart.
    """
    engine = RulesEngine.load(RULES_PATH)
    flow = yaml.safe_load(FLOW_PATH.read_text(encoding="utf-8"))
    sources = engine.legal_sources

    materials = []
    for row in engine.raw["materials"]:
        resolved = engine.resolve(row["class"])
        materials.append(
            {
                "class": row["class"],
                "local_names": row.get("local_names", []),
                "pathway": resolved.pathway_id,
                "animation": flow["pathway_animation"][resolved.pathway_id],
                "price": {
                    "low": resolved.price.low,
                    "high": resolved.price.high,
                    "display": resolved.price.display(),
                    "has_market": resolved.price.has_market,
                    "confidence": resolved.price.confidence,
                    "as_of": resolved.price.as_of,
                },
                "prep_tl": row.get("prep_tl", ""),
                "prep_en": row.get("prep_en", ""),
                "is_critical_class": bool(row.get("is_critical_class")),
                "often_refused": bool(row.get("often_refused")),
                "epr_covered": bool(row.get("epr_covered")),
                "resin_code": row.get("resin_code"),
                "typical_unit_mass_g": row.get("typical_unit_mass_g"),
                "citations": [
                    {
                        "citation": sources[cid].citation,
                        "verified": sources[cid].verified,
                    }
                    for cid in row.get("citations", [])
                    if cid in sources
                ],
                # The gate the UI must honour: false means show the guidance, but do
                # not attribute it to the municipality.
                "presentable_as_official": resolved.is_presentable_as_official,
                "warnings": resolved.warnings,
            }
        )

    report = engine.verification_report()

    return {
        "generated_from": [
            str(RULES_PATH.relative_to(REPO_ROOT)),
            str(FLOW_PATH.relative_to(REPO_ROOT)),
        ],
        "schema_version": engine.raw["meta"]["schema_version"],
        "status": engine.raw["meta"]["status"],
        "updated_on": str(engine.raw["meta"]["updated_on"]),
        "verification": {
            "legal_sources_total": report["legal_sources_total"],
            "legal_sources_verified": report["legal_sources_verified"],
            "phase1_gate_met": report["phase1_gate_met"],
            "verified_shops": report["verified_shops"],
            "phase2_gate_met": report["phase2_gate_met"],
        },
        "price_provenance": engine.raw.get("price_provenance", {}),
        "pathways": engine.raw["pathways"],
        "materials": materials,
        "overrides": [
            {
                "id": o["id"],
                "when": o.get("when", {}),
                "pathway": o["pathway"],
                "animation": flow["pathway_animation"][o["pathway"]],
                "reason_tl": o.get("reason_tl", ""),
                "reason_en": o.get("reason_en", ""),
                # Replaces the material's prep text when this override fires.
                "prep_tl": o.get("prep_tl", ""),
                "prep_en": o.get("prep_en", ""),
            }
            for o in engine.raw.get("overrides", [])
        ],
        "flow": {
            "kind": flow["meta"]["kind"],
            "verification": flow["meta"]["verification"],
            "caveat": flow["meta"]["caveat"],
            "leakage": flow["leakage"],
            "recovery": flow["recovery"],
        },
        # Barangay selection replaces GPS in v1 — see web/README.md. Sourced from
        # scrapers/psa_psgc.py's expected list; reconciled against PSGC on harvest.
        "barangays": [
            "San Andres",
            "San Isidro",
            "San Juan",
            "San Roque",
            "Santa Rosa",
            "Santo Domingo",
            "Santo Niño",
        ],
    }


def serialise(bundle: dict) -> str:
    return json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed bundle differs from a fresh build.",
    )
    args = parser.parse_args()

    payload = serialise(build())

    if args.check:
        if not OUTPUT_PATH.exists():
            print(f"{OUTPUT_PATH.relative_to(REPO_ROOT)} is missing. Run this script.")
            return 1
        if OUTPUT_PATH.read_text(encoding="utf-8") != payload:
            print(
                f"{OUTPUT_PATH.relative_to(REPO_ROOT)} is stale — the rules YAML has "
                "changed since it was built.\nRun: python scripts/build_app_data.py"
            )
            return 1
        print("App data bundle is in sync with the rules YAML.")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(payload, encoding="utf-8")
    bundle = json.loads(payload)
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  materials              : {len(bundle['materials'])}")
    print(
        f"  legal sources verified : {bundle['verification']['legal_sources_verified']}"
        f"/{bundle['verification']['legal_sources_total']}"
    )
    print(f"  verified junkshops     : {bundle['verification']['verified_shops']}")
    official = sum(1 for m in bundle["materials"] if m["presentable_as_official"])
    print(f"  presentable as official: {official}/{len(bundle['materials'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
