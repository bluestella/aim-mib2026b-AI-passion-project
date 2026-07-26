"""Harvest Cainta LGU ordinances and resolutions (plan §3, Tier 1).

cainta.gov.ph is Wix-generated: the pages are HTML shells and the documents
themselves sit at hashed asset paths under ``/_files/ugd/<hash>.pdf``. So the
job is two-step -- scrape the index pages for asset links, then fetch each PDF
once and never again.

The link text on those pages is where the ordinance number lives ("Ordinance
No. 2023-012 ..."), and it is the only structured metadata available before
the PDF is parsed. ``parse_document_links`` pulls it out so the harvest
manifest is searchable without opening a single PDF.

Run:
    python -m scrapers.cainta_ordinances            # harvest everything
    python -m scrapers.cainta_ordinances --dry-run  # list links, fetch nothing
"""

from __future__ import annotations

import argparse
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser

from scrapers.common import PoliteFetcher, ScrapeRefused, write_interim

SOURCE_ID = "cainta_ordinances"

INDEX_PAGES = {
    "resolutions_and_ordinances": "https://www.cainta.gov.ph/resolutionsandordinances",
    "barangays": "https://www.cainta.gov.ph/barangays",
    "departments_and_offices": "https://www.cainta.gov.ph/departments-and-offices",
    "full_disclosure": "https://www.cainta.gov.ph/fulldisclosure",
}

#: Ordinances the plan calls out by name. Presence of these in the harvest is
#: the Phase-1 completeness check -- if 2023-012 is missing, the rules engine
#: has no legal anchor and Phase 1's gate is not met.
PRIORITY_ORDINANCES = {
    "2016-013": "Segregation at source",
    "2022-002": "Anti-littering",
    "2022-010": "Segregation at source (amending/reinforcing)",
    "2023-005": "Data Privacy Act operationalisation",
    "2023-012": "Environmental Protection and Waste Management Code of 2023",
}

DOCUMENT_SUFFIXES = (".pdf", ".doc", ".docx")

_ORDINANCE_RE = re.compile(
    r"\b(?:ordinance|ord\.?|resolution|res\.?)\s*(?:no\.?)?\s*(\d{4}[-–]\d{2,4})",
    re.IGNORECASE,
)


@dataclass
class DocumentLink:
    url: str
    text: str
    ordinance_no: str | None
    index_page: str


class _LinkExtractor(HTMLParser):
    """Collect ``(href, visible text)`` pairs for document links only."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._buffer).strip()))
            self._href = None
            self._buffer = []


def parse_document_links(html: str, index_page: str) -> list[DocumentLink]:
    """Extract document links from a Wix page's HTML.

    Matches both the ``/_files/ugd/`` asset convention and any absolute link
    ending in a document suffix, since Cainta's Full Disclosure page has
    historically mixed the two.
    """
    extractor = _LinkExtractor()
    extractor.feed(html)

    seen: set[str] = set()
    out: list[DocumentLink] = []
    for href, text in extractor.links:
        url = _absolutise(href)
        if not _is_document(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(
            DocumentLink(
                url=url,
                text=re.sub(r"\s+", " ", text),
                ordinance_no=extract_ordinance_no(text),
                index_page=index_page,
            )
        )
    return out


def extract_ordinance_no(text: str) -> str | None:
    """Pull "2023-012" out of link text like "Ordinance No. 2023-012 - ..."."""
    match = _ORDINANCE_RE.search(text or "")
    if not match:
        return None
    return match.group(1).replace("–", "-")


def _absolutise(href: str) -> str:
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://www.cainta.gov.ph" + href
    return href


def _is_document(url: str) -> bool:
    lowered = url.lower().split("?")[0]
    if "/_files/ugd/" in lowered:
        return True
    return lowered.startswith("http") and lowered.endswith(DOCUMENT_SUFFIXES)


def harvest(dry_run: bool = False) -> list[dict]:
    fetcher = PoliteFetcher(SOURCE_ID)
    records: list[dict] = []

    for page_name, url in INDEX_PAGES.items():
        try:
            html = fetcher.get_text(url)
        except ScrapeRefused as exc:
            print(f"[refused] {page_name}: {exc}")
            continue
        except Exception as exc:  # network, 404, Wix rendering change
            print(f"[error]   {page_name}: {exc}")
            continue

        links = parse_document_links(html, page_name)
        print(f"[index]   {page_name}: {len(links)} document link(s)")

        for link in links:
            row = asdict(link)
            if dry_run:
                records.append(row)
                continue
            try:
                result = fetcher.fetch(link.url)
            except Exception as exc:
                print(f"[error]   {link.url}: {exc}")
                row["error"] = str(exc)
            else:
                row["local_path"] = str(result.path)
                row["sha256"] = result.sha256
                row["from_cache"] = result.from_cache
            records.append(row)

    write_interim(SOURCE_ID, "document_index.json", records)
    _report_priority_coverage(records)
    return records


def _report_priority_coverage(records: list[dict]) -> None:
    """State plainly which plan-critical ordinances the harvest did and did not find."""
    found = {r.get("ordinance_no") for r in records if r.get("ordinance_no")}
    print("\nPriority ordinance coverage (plan §3 Tier 1.1):")
    for number, description in sorted(PRIORITY_ORDINANCES.items()):
        mark = "found  " if number in found else "MISSING"
        print(f"  [{mark}] {number}  {description}")
    missing = set(PRIORITY_ORDINANCES) - found
    if missing:
        print(
            "\n  Missing ordinances are a Phase-1 blocker: rules/cainta_disposal_rules.yaml\n"
            "  cannot cite a document that was never retrieved. Fall back to FOI request C\n"
            "  (docs/foi_requests/) or the Sangguniang Bayan archive before hardcoding rules."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List discovered document links without downloading them.",
    )
    args = parser.parse_args()
    harvest(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
