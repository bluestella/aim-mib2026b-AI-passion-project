"""Resolve Cainta's canonical barangay codes from PSA PSGC (plan §3, Tier 2.9).

The plan's n=7 problem starts here. Seven barangays cannot support supervised
learning, so PSGC codes are used for *labelling and joining* -- never as a
modelling unit. Spatial features live on H3 r9 cells (see ``daloy.spatial``).

PSA issues quarterly PSGC corrections, so the barangay list is reconciled
against ``EXPECTED_BARANGAYS`` on every run and any drift is printed loudly
rather than silently absorbed.

If PSA's robots.txt disallows this path, the fetcher refuses and says so. That
is the correct outcome, not a bug to work around: the same table is published
in the downloadable PSGC publication file, which is the route to use instead.

Run:
    python -m scrapers.psa_psgc
"""

from __future__ import annotations

import argparse
import html
import re
import unicodedata

from scrapers.common import PoliteFetcher, ScrapeRefused, write_interim

SOURCE_ID = "psa_psgc"

CAINTA_PSGC = "0405805000"
PSGC_URL = f"https://psa.gov.ph/classification/psgc/barangays/{CAINTA_PSGC}"

#: From the plan, Appendix A. Verify, do not trust.
EXPECTED_BARANGAYS = (
    "San Andres",
    "San Isidro",
    "San Juan",
    "San Roque",
    "Santa Rosa",
    "Santo Domingo",
    "Santo Nino",
)

#: Reference figures from PSA 2024 POPCEN, carried here so anything that
#: consumes them can cite a source and a date rather than a folk memory.
POPCEN_2024 = {
    "population": 386_321,
    "households": 90_707,
    "land_area_km2": 42.99,
    "barangay_count": 7,
    "source": "PSA 2024 POPCEN",
    "as_of": "2024",
    "verified": False,
}

_BARANGAY_ROW_RE = re.compile(
    r"(?P<code>\d{10})\s*</td>\s*<td[^>]*>\s*(?P<name>[^<]+?)\s*</td>",
    re.IGNORECASE,
)


def normalise_name(name: str) -> str:
    """Fold entities, accents and whitespace so 'Santo Niño' matches 'Santo Nino'.

    PSA serves the tilde as the HTML entity ``&ntilde;``, and this module reads
    raw markup with a regex rather than a DOM parser, so entity decoding has to
    happen here or 'Santo Niño' silently fails to reconcile.
    """
    decomposed = unicodedata.normalize("NFKD", html.unescape(name))
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", stripped).strip().casefold()


def parse_barangays(markup: str) -> list[dict]:
    """Extract (psgc_code, name) pairs from the PSGC barangay table."""
    seen: set[str] = set()
    rows: list[dict] = []
    for match in _BARANGAY_ROW_RE.finditer(markup):
        code = match.group("code")
        name = re.sub(r"\s+", " ", html.unescape(match.group("name"))).strip()
        if code in seen or not name:
            continue
        seen.add(code)
        rows.append({"psgc_code": code, "name": name, "normalised": normalise_name(name)})
    return rows


def reconcile(rows: list[dict]) -> dict:
    """Compare the scraped list against the plan's hardcoded expectation."""
    got = {row["normalised"] for row in rows}
    expected = {normalise_name(name) for name in EXPECTED_BARANGAYS}
    return {
        "count_scraped": len(rows),
        "count_expected": len(expected),
        "missing_from_scrape": sorted(expected - got),
        "unexpected_in_scrape": sorted(got - expected),
        "matches": got == expected,
    }


def harvest() -> dict:
    fetcher = PoliteFetcher(SOURCE_ID)
    payload: dict = {
        "psgc_code": CAINTA_PSGC,
        "url": PSGC_URL,
        "popcen_2024": POPCEN_2024,
    }

    try:
        markup = fetcher.get_text(PSGC_URL)
    except ScrapeRefused as exc:
        print(f"[refused] {exc}")
        print(
            "\nUse the downloadable PSGC publication file from psa.gov.ph instead,\n"
            "place it under data/raw/psa_psgc/, and parse it offline."
        )
        payload["error"] = str(exc)
        write_interim(SOURCE_ID, "cainta_barangays.json", payload)
        return payload
    except Exception as exc:
        print(f"[error]   {exc}")
        payload["error"] = str(exc)
        write_interim(SOURCE_ID, "cainta_barangays.json", payload)
        return payload

    rows = parse_barangays(markup)
    check = reconcile(rows)
    payload["barangays"] = rows
    payload["reconciliation"] = check
    write_interim(SOURCE_ID, "cainta_barangays.json", payload)

    print(f"Scraped {check['count_scraped']} barangay(s) for PSGC {CAINTA_PSGC}.")
    for row in rows:
        print(f"  {row['psgc_code']}  {row['name']}")
    if check["matches"]:
        print("\nMatches the expected seven barangays.")
    else:
        print("\nPSGC DRIFT -- the hardcoded list in this module is now wrong:")
        if check["missing_from_scrape"]:
            print(f"  expected but not found: {check['missing_from_scrape']}")
        if check["unexpected_in_scrape"]:
            print(f"  found but not expected: {check['unexpected_in_scrape']}")
        print("  Update EXPECTED_BARANGAYS and anything joined on barangay name.")
    return payload


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    harvest()


if __name__ == "__main__":
    main()
