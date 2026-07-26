"""Seed the local knowledge graph from OpenStreetMap (plan §3, Tier 4.1).

Two very different things come out of one query:

  * **Recovery nodes** -- junkshops, MRFs, transfer stations. Expect almost
    nothing. Philippine junkshops are systematically under-mapped and the
    tagging convention is inconsistent, so OSM is a seed for the field survey,
    not a substitute for it. The count this script prints is the honest
    starting point for Phase 2, and it is meant to look disappointing.
  * **The leakage network** -- ``waterway`` ways, which are the geometry the
    Flow Simulation traverses (plan §2.2). These are usually mapped far better
    than the junkshops, because rivers are visible from satellite imagery and
    scrap yards are not.

OSM data is ODbL. Attribute it in the app, and contribute the field survey
back (plan §7.7).

Run:
    python -m scrapers.osm_overpass
    python -m scrapers.osm_overpass --print-query   # inspect, don't fetch
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

from scrapers.common import PoliteFetcher, write_interim

SOURCE_ID = "osm_overpass"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

#: Approximate Cainta envelope (S, W, N, E). Tighten against the official
#: PSGC/PSA boundary before production -- this box overlaps Pasig and Taytay,
#: so every result must be point-in-polygon filtered before it reaches a user.
BBOX = (14.545, 121.085, 14.620, 121.145)

RECOVERY_SELECTORS = (
    'nwr["amenity"="recycling"]',
    'nwr["shop"="scrap_yard"]',
    'nwr["amenity"="waste_transfer_station"]',
    'nwr["amenity"="waste_disposal"]',
    'nwr["landuse"="landfill"]',
)
WATERWAY_SELECTORS = ('way["waterway"~"stream|drain|ditch|river|canal"]',)
ANCHOR_SELECTORS = (
    'nwr["amenity"="school"]',
    'nwr["amenity"="marketplace"]',
)

CATEGORIES = {
    "recovery": RECOVERY_SELECTORS,
    "waterway": WATERWAY_SELECTORS,
    "anchor": ANCHOR_SELECTORS,
}


def build_query(bbox: tuple[float, float, float, float] = BBOX) -> str:
    box = ",".join(str(v) for v in bbox)
    lines = ["[out:json][timeout:60];", "("]
    for category, selectors in CATEGORIES.items():
        lines.append(f"  // {category}")
        lines.extend(f"  {selector}({box});" for selector in selectors)
    lines.extend([");", "out center tags;"])
    return "\n".join(lines)


def classify(tags: dict[str, str]) -> str:
    """Bucket an OSM element into recovery / waterway / anchor / other."""
    if tags.get("waterway"):
        return "waterway"
    if (
        tags.get("amenity")
        in {"recycling", "waste_transfer_station", "waste_disposal"}
        or tags.get("shop") == "scrap_yard"
        or tags.get("landuse") == "landfill"
    ):
        return "recovery"
    if tags.get("amenity") in {"school", "marketplace"}:
        return "anchor"
    return "other"


def normalise(payload: dict) -> list[dict]:
    """Flatten an Overpass response into rows keyed for the knowledge graph.

    ``out center`` gives ways and relations a synthetic centre point, so nodes
    and areas can share one schema. Waterways keep no geometry here -- routing
    needs the full polyline, which is a Phase-3 concern handled separately.
    """
    rows: list[dict] = []
    for element in payload.get("elements", []):
        tags = element.get("tags", {}) or {}
        center = element.get("center") or {}
        rows.append(
            {
                "osm_type": element.get("type"),
                "osm_id": element.get("id"),
                "category": classify(tags),
                "name": tags.get("name"),
                "lat": element.get("lat", center.get("lat")),
                "lon": element.get("lon", center.get("lon")),
                "tags": tags,
            }
        )
    return rows


def harvest(bbox: tuple[float, float, float, float] = BBOX) -> list[dict]:
    query = build_query(bbox)
    fetcher = PoliteFetcher(SOURCE_ID)

    # Overpass takes the query as a POST body, so this bypasses
    # PoliteFetcher.fetch; the session still carries the honest User-Agent and
    # the call is one request per run.
    fetcher._throttle(OVERPASS_URL)  # noqa: SLF001 -- deliberate: same rate-limit budget
    response = fetcher.session.post(OVERPASS_URL, data={"data": query}, timeout=120)
    response.raise_for_status()
    payload = response.json()

    raw_path = fetcher.out_dir / "overpass_cainta.json"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    rows = normalise(payload)
    write_interim(SOURCE_ID, "osm_nodes.json", rows)
    _report(rows)
    return rows


def _report(rows: list[dict]) -> None:
    counts = Counter(row["category"] for row in rows)
    print("OSM elements inside the Cainta bounding box:")
    for category in ("recovery", "waterway", "anchor", "other"):
        print(f"  {category:9s} {counts.get(category, 0)}")

    recovery = counts.get("recovery", 0)
    named = sum(1 for r in rows if r["category"] == "recovery" and r.get("name"))
    print(
        f"\n{recovery} recovery node(s), {named} of them named. "
        "The plan's target is 30-60 verified junkshops (Phase 2 gate: >=25).\n"
        "Whatever the number above, treat it as a seed list for fieldwork, and\n"
        "contribute the survey back to OSM under ODbL when it is done."
    )
    print(
        "\nNote: the bounding box overlaps Pasig and Taytay. Point-in-polygon\n"
        "filter against the PSA/PSGC Cainta boundary before any of this is shown\n"
        "to a user as 'in Cainta'."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-query",
        action="store_true",
        help="Print the Overpass QL and exit without contacting the API.",
    )
    args = parser.parse_args()
    if args.print_query:
        print(build_query())
        return
    harvest()


if __name__ == "__main__":
    main()
