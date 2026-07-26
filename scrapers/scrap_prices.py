"""Track commodity scrap prices as a lag feature (plan §3, Tier 4.2-4.3).

Junkshop counter prices are downstream of commodity indices, so this appends
one observation per run to a tidy time series. That series is the covariate
set for the ``price_php_per_kg`` regression in plan §5.3, which needs roughly
30 shops x 12 weeks before it is worth fitting -- meaning this scraper's job
is to start accumulating history *now*, long before there is a model.

Two honest caveats:

  * Published national scrap indices are a *driver* of junkshop bid prices,
    not the prices themselves. A Cainta junkshop pays well below index. Never
    show an index price to a user as a junkshop price.
  * The site layout will change. The parser below is intentionally shallow and
    fails loudly to a manual-entry path rather than guessing.

Run:
    python -m scrapers.scrap_prices
    python -m scrapers.scrap_prices --manual copper=352 aluminium=61
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import date
from pathlib import Path

from scrapers.common import REPO_ROOT, PoliteFetcher

SOURCE_ID = "scrap_prices"
SOURCE_URL = "https://scrap.trade/scrap-prices/philippines/"

SERIES_PATH = REPO_ROOT / "data" / "interim" / SOURCE_ID / "commodity_prices.csv"
FIELDNAMES = ("observed_on", "material", "price_php_per_kg", "source", "method")

#: Materials worth tracking, mapped to the material_class taxonomy in
#: rules/cainta_disposal_rules.yaml so the join is unambiguous later.
TRACKED = {
    "copper": "copper_wire",
    "aluminium": "aluminium_can",
    "aluminum": "aluminium_can",
    "steel": "ferrous_metal",
    "iron": "ferrous_metal",
    "pet": "PET_bottle",
}


def parse_prices(html: str) -> dict[str, float]:
    """Best-effort scrape of ``material -> PHP/kg`` from the price page.

    Deliberately conservative: it looks for a tracked material name followed
    within a short span by a peso figure. Anything it cannot read confidently
    is left out, so a layout change yields an empty result and a visible
    warning rather than a plausible-looking wrong number.
    """
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    found: dict[str, float] = {}
    for keyword, material_class in TRACKED.items():
        pattern = re.compile(
            rf"{keyword}\b.{{0,80}}?(?:php|₱|p)\s*([\d,]+(?:\.\d+)?)",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            continue
        try:
            value = float(match.group(1).replace(",", ""))
        except ValueError:
            continue
        # First match wins; TRACKED maps synonyms onto one class.
        found.setdefault(material_class, value)
    return found


def append_observations(
    prices: dict[str, float], source: str, method: str, observed_on: date | None = None
) -> Path:
    """Append rows to the tidy series, creating the file with a header if new."""
    SERIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new = not SERIES_PATH.exists()
    day = (observed_on or date.today()).isoformat()

    with SERIES_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        if is_new:
            writer.writeheader()
        for material, price in sorted(prices.items()):
            writer.writerow(
                {
                    "observed_on": day,
                    "material": material,
                    "price_php_per_kg": price,
                    "source": source,
                    "method": method,
                }
            )
    return SERIES_PATH


def harvest() -> dict[str, float]:
    fetcher = PoliteFetcher(SOURCE_ID)
    try:
        html = fetcher.get_text(SOURCE_URL)
    except Exception as exc:
        print(f"[error] {SOURCE_URL}: {exc}")
        print("Fall back to --manual entry so the series keeps a continuous record.")
        return {}

    prices = parse_prices(html)
    if not prices:
        print(
            "Parsed no prices. The page layout has probably changed -- read it by\n"
            "hand and record today's figures with:\n"
            "  python -m scrapers.scrap_prices --manual copper=<php> aluminium=<php>"
        )
        return {}

    append_observations(prices, source=SOURCE_URL, method="scraped")
    for material, price in sorted(prices.items()):
        print(f"  {material:18s} PHP {price:>8.2f}/kg")
    print(f"\nAppended to {SERIES_PATH.relative_to(REPO_ROOT)}")
    print(
        "Reminder: these are commodity index prices, not Cainta junkshop counter\n"
        "prices. Do not display them to users as what a shop will pay."
    )
    return prices


def _parse_manual(pairs: list[str]) -> dict[str, float]:
    prices: dict[str, float] = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        material_class = TRACKED.get(key.strip().lower(), key.strip())
        prices[material_class] = float(value)
    return prices


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manual",
        nargs="+",
        metavar="MATERIAL=PHP",
        help="Record hand-read prices instead of scraping, e.g. copper=352.",
    )
    args = parser.parse_args()

    if args.manual:
        prices = _parse_manual(args.manual)
        append_observations(prices, source="manual entry", method="manual")
        print(f"Recorded {len(prices)} manual observation(s) to {SERIES_PATH}")
        return
    harvest()


if __name__ == "__main__":
    main()
