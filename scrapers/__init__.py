"""Data harvesters for DALOY Scan.

Every module here routes its HTTP through ``scrapers.common.PoliteFetcher``, which
enforces the governance rules in docs/DATA_AND_ML_PLAN.md §7 — robots.txt, a 2-second
rate limit, an honest User-Agent, content-hash caching, and a provenance manifest.

Run any of them as a module:

    python -m scrapers.cainta_ordinances --dry-run
    python -m scrapers.nswmc_reports
    python -m scrapers.psa_psgc
    python -m scrapers.osm_overpass --print-query
    python -m scrapers.scrap_prices
    python -m scrapers.foi_tracker status
"""
