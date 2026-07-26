"""Tests for scraper parsing and governance.

Deliberately offline: every test here runs against fixture strings, so the
suite never touches a government server. The parsing logic is what breaks when
a site is redesigned, and it is what these tests pin down.
"""

from __future__ import annotations

from datetime import date

import pytest
from scrapers.cainta_ordinances import extract_ordinance_no, parse_document_links
from scrapers.common import PoliteFetcher, ScrapeRefused, _filename_for
from scrapers.foi_tracker import add_working_days, deadline_for, working_days_between
from scrapers.osm_overpass import build_query, classify, normalise
from scrapers.psa_psgc import normalise_name, parse_barangays, reconcile
from scrapers.scrap_prices import parse_prices

# --- governance ---------------------------------------------------------


def test_facebook_is_refused_by_construction() -> None:
    """Plan §7.4 — a comment is easy to ignore, an exception is not."""
    fetcher = PoliteFetcher("test")
    with pytest.raises(ScrapeRefused, match="denylist"):
        fetcher.fetch("https://www.facebook.com/onecainta.onecainta")


def test_user_agent_identifies_the_project() -> None:
    from scrapers.common import USER_AGENT

    assert "DALOY-Scan-Research" in USER_AGENT
    assert "contact:" in USER_AGENT


def test_min_delay_meets_the_plans_rate_limit() -> None:
    from scrapers.common import MIN_DELAY_SECONDS

    assert MIN_DELAY_SECONDS >= 2.0


def test_wix_asset_urls_get_stable_unique_filenames() -> None:
    """Hashed Wix paths share basenames, so names must not collide."""
    a = _filename_for("https://www.cainta.gov.ph/_files/ugd/aaa111_doc.pdf")
    b = _filename_for("https://www.cainta.gov.ph/_files/ugd/bbb222_doc.pdf")
    assert a != b
    assert a == _filename_for("https://www.cainta.gov.ph/_files/ugd/aaa111_doc.pdf")
    assert a.endswith(".pdf")


# --- Cainta ordinances --------------------------------------------------

WIX_FIXTURE = """
<html><body>
  <a href="/_files/ugd/abc123_ordinance2023012.pdf">Ordinance No. 2023-012 - Environmental Code</a>
  <a href="/_files/ugd/def456_ord2022010.pdf">Ordinance No. 2022-010 Segregation at Source</a>
  <a href="https://www.cainta.gov.ph/reports/sre-2025.pdf">SRE Q1 2025</a>
  <a href="/barangays">Barangays</a>
  <a href="https://www.facebook.com/onecainta">Follow us</a>
  <a href="/_files/ugd/abc123_ordinance2023012.pdf">Duplicate link</a>
</body></html>
"""


def test_parses_only_document_links() -> None:
    links = parse_document_links(WIX_FIXTURE, "test_page")
    urls = [link.url for link in links]
    assert len(links) == 3, "HTML nav links and the Facebook link must not be collected"
    assert all(url.endswith(".pdf") for url in urls)
    assert not any("facebook" in url for url in urls)


def test_duplicate_links_are_collapsed() -> None:
    links = parse_document_links(WIX_FIXTURE, "test_page")
    assert len(links) == len({link.url for link in links})


def test_relative_wix_paths_are_absolutised() -> None:
    links = parse_document_links(WIX_FIXTURE, "test_page")
    assert all(link.url.startswith("https://") for link in links)


def test_ordinance_number_extracted_from_link_text() -> None:
    links = parse_document_links(WIX_FIXTURE, "test_page")
    numbers = {link.ordinance_no for link in links}
    assert "2023-012" in numbers
    assert "2022-010" in numbers


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Ordinance No. 2023-012", "2023-012"),
        ("ORD. 2022-010 something", "2022-010"),
        ("Resolution No. 2016-013", "2016-013"),
        ("Ordinance 2023–005 en dash", "2023-005"),
        ("Annual Report 2024", None),
        ("", None),
    ],
)
def test_ordinance_number_patterns(text: str, expected: str | None) -> None:
    assert extract_ordinance_no(text) == expected


# --- PSGC ---------------------------------------------------------------

PSGC_FIXTURE = """
<table>
 <tr><td>0405805001</td><td>San Andres</td></tr>
 <tr><td>0405805002</td><td>San Isidro</td></tr>
 <tr><td>0405805003</td><td>San Juan</td></tr>
 <tr><td>0405805004</td><td>San Roque</td></tr>
 <tr><td>0405805005</td><td>Santa Rosa</td></tr>
 <tr><td>0405805006</td><td>Santo Domingo</td></tr>
 <tr><td>0405805007</td><td>Santo Ni&ntilde;o</td></tr>
</table>
"""


def test_parses_all_seven_barangays() -> None:
    rows = parse_barangays(PSGC_FIXTURE)
    assert len(rows) == 7
    assert rows[0]["psgc_code"] == "0405805001"


def test_accented_barangay_name_reconciles() -> None:
    """'Santo Niño' must match the ASCII 'Santo Nino' in the expected list."""
    assert normalise_name("Santo Niño") == normalise_name("Santo Nino")
    check = reconcile(parse_barangays(PSGC_FIXTURE))
    assert check["matches"], check


def test_psgc_drift_is_surfaced_not_swallowed() -> None:
    """A renamed or added barangay must show up as drift."""
    drifted = PSGC_FIXTURE.replace(
        "<tr><td>0405805007</td><td>Santo Ni&ntilde;o</td></tr>",
        "<tr><td>0405805008</td><td>New Barangay</td></tr>",
    )
    check = reconcile(parse_barangays(drifted))
    assert not check["matches"]
    assert check["unexpected_in_scrape"]
    assert check["missing_from_scrape"]


# --- Overpass -----------------------------------------------------------


def test_query_covers_every_category() -> None:
    query = build_query()
    assert 'nwr["amenity"="recycling"]' in query
    assert 'way["waterway"~"stream|drain|ditch|river|canal"]' in query
    assert "out center tags;" in query


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ({"amenity": "recycling"}, "recovery"),
        ({"shop": "scrap_yard"}, "recovery"),
        ({"landuse": "landfill"}, "recovery"),
        ({"waterway": "drain"}, "waterway"),
        ({"amenity": "school"}, "anchor"),
        ({"amenity": "cafe"}, "other"),
        ({}, "other"),
    ],
)
def test_element_classification(tags: dict, expected: str) -> None:
    assert classify(tags) == expected


def test_ways_get_a_centre_point_so_schema_stays_flat() -> None:
    payload = {
        "elements": [
            {"type": "node", "id": 1, "lat": 14.57, "lon": 121.12, "tags": {"shop": "scrap_yard"}},
            {
                "type": "way",
                "id": 2,
                "center": {"lat": 14.58, "lon": 121.13},
                "tags": {"waterway": "drain"},
            },
            {"type": "way", "id": 3, "tags": {}},
        ]
    }
    rows = normalise(payload)
    assert rows[0]["category"] == "recovery"
    assert rows[1]["lat"] == 14.58
    assert rows[2]["lat"] is None


# --- prices -------------------------------------------------------------


def test_prices_map_onto_the_material_taxonomy() -> None:
    html = "<td>Copper scrap</td><td>PHP 352.00</td><td>Aluminium cans</td><td>₱61.50</td>"
    prices = parse_prices(html)
    assert prices["copper_wire"] == pytest.approx(352.0)
    assert prices["aluminium_can"] == pytest.approx(61.5)


def test_unreadable_page_yields_nothing_rather_than_a_guess() -> None:
    """A layout change must not produce a plausible wrong number."""
    assert parse_prices("<html><body>Site under maintenance</body></html>") == {}


# --- FOI clock ----------------------------------------------------------


def test_working_days_skip_weekends() -> None:
    friday = date(2026, 7, 24)
    assert friday.weekday() == 4
    assert add_working_days(friday, 1) == date(2026, 7, 27)  # Monday


def test_eo2_response_deadline_is_15_working_days() -> None:
    filed = date(2026, 8, 3)  # a Monday
    deadline = deadline_for(filed, today=filed)
    assert deadline.due_on == date(2026, 8, 24)
    assert deadline.working_days_remaining == 15
    assert not deadline.overdue


def test_extension_adds_20_working_days() -> None:
    filed = date(2026, 8, 3)
    plain = deadline_for(filed, today=filed)
    extended = deadline_for(filed, extended=True, today=filed)
    assert extended.due_on > plain.due_on
    assert extended.working_days_remaining == 35


def test_overdue_request_is_flagged() -> None:
    filed = date(2026, 1, 5)
    deadline = deadline_for(filed, today=date(2026, 7, 26))
    assert deadline.overdue
    assert deadline.working_days_remaining < 0


def test_working_days_between_is_signed() -> None:
    a, b = date(2026, 8, 3), date(2026, 8, 10)
    assert working_days_between(a, b) == 5
    assert working_days_between(b, a) == -5
