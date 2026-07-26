"""Harvest the NSWMC / DENR-EMB national PDF corpus (plan §3, Tier 2).

These documents supply structure and denominators, not training rows: the
SCMAR form defines the field dictionary a Philippine LGU is legally required
to hold, and the status reports supply the national priors (composition
percentages, per-capita generation) the app quotes when Cainta-specific
numbers do not exist.

The URLs are pinned rather than discovered. EMB reorganises its WordPress
uploads directory periodically, so a broken URL here is a signal worth seeing
in the log -- not something a crawler should paper over by wandering the site.

Run:
    python -m scrapers.nswmc_reports
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from scrapers.common import PoliteFetcher, write_interim

SOURCE_ID = "nswmc_reports"


@dataclass(frozen=True)
class Document:
    key: str
    url: str
    why: str
    #: True where the document defines schema/law we depend on structurally.
    #: A failed fetch on one of these blocks Phase 1; the rest are nice to have.
    critical: bool = False


DOCUMENTS = (
    Document(
        key="lgu_swm_scmar_form",
        url="https://nswmc.emb.gov.ph/wp-content/uploads/2016/09/"
        "LGU-SWM-SCMAR-revised-March-2016.pdf",
        why="Canonical LGU SWM reporting schema -- the feature dictionary (plan §3, 2.1).",
        critical=True,
    ),
    Document(
        key="ra9003_irr",
        url="https://nswmc.emb.gov.ph/wp-content/uploads/2025/04/RA-9003-IRR.pdf",
        why="Legal definitions for the material taxonomy; BSWMC and MRF requirements.",
        critical=True,
    ),
    Document(
        key="national_swm_status_report",
        url="https://nswmc.emb.gov.ph/wp-content/uploads/2016/06/"
        "Solid-Wastefinaldraft-12.29.15.pdf",
        why="MSW composition %, per-capita generation rates, MRF counts by region.",
    ),
    Document(
        key="sanitary_landfill_inventory",
        url="https://nswmc.emb.gov.ph/wp-content/uploads/2021/06/landfills-may2021.pdf",
        why="SLF locations and LGUs served, including Rizal -- terminus of the residual path.",
    ),
    Document(
        key="swm_plan_formulation_guidebook",
        url="https://nswmc.emb.gov.ph/wp-content/uploads/2017/09/FSWMP-Proof-Layout.pdf",
        why="Collection route / service-area structure; 'no segregation no collection' patterns.",
    ),
)


def harvest() -> list[dict]:
    fetcher = PoliteFetcher(SOURCE_ID)
    records: list[dict] = []
    failures_critical: list[str] = []

    for doc in DOCUMENTS:
        row = {"key": doc.key, "url": doc.url, "why": doc.why, "critical": doc.critical}
        try:
            result = fetcher.fetch(doc.url, filename=f"{doc.key}.pdf")
        except Exception as exc:
            row["error"] = str(exc)
            print(f"[error]  {doc.key}: {exc}")
            if doc.critical:
                failures_critical.append(doc.key)
        else:
            row["local_path"] = str(result.path)
            row["sha256"] = result.sha256
            row["from_cache"] = result.from_cache
            state = "cached" if result.from_cache else "fetched"
            print(f"[{state}] {doc.key}")
        records.append(row)

    write_interim(SOURCE_ID, "document_index.json", records)

    if failures_critical:
        print(
            "\nCritical documents failed to download: "
            + ", ".join(failures_critical)
            + "\nEMB moves its uploads paths periodically. Re-locate the document on\n"
            "nswmc.emb.gov.ph and update the pinned URL in this module rather than\n"
            "crawling the site."
        )
    return records


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    harvest()


if __name__ == "__main__":
    main()
