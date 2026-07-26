"""Shared, polite HTTP plumbing for every DALOY Scan scraper.

This module exists so the governance rules in docs/DATA_AND_ML_PLAN.md §7 are
enforced in one place instead of being re-remembered in six scrapers:

  * robots.txt is consulted before the first fetch on any host, and a
    disallowed URL raises rather than being fetched (§7.1);
  * requests to the same host are spaced by MIN_DELAY_SECONDS (§7.2);
  * the User-Agent identifies the project and a contact address (§7.2);
  * responses are cached to data/raw/ by content hash, so an unchanged
    government PDF is downloaded exactly once (§7.3);
  * every fetch appends a provenance row to the manifest, so any figure that
    later reaches a slide can be traced back to a URL and a date (§7.8).

Hosts on DENYLIST are refused outright. Facebook is there deliberately: the
plan forbids automating it, and a comment is easier to ignore than an
exception.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "_manifest.jsonl"

CONTACT = os.environ.get("DALOY_CONTACT_EMAIL", "unset-contact@example.org")
USER_AGENT = (
    f"DALOY-Scan-Research/1.0 (zero-waste civic app, Cainta; contact: {CONTACT})"
)

MIN_DELAY_SECONDS = 2.0
TIMEOUT_SECONDS = 60

#: Hosts we will never automate against, with the reason. See plan §3 (1.6) and §7.4.
DENYLIST = {
    "facebook.com": "Meta ToS forbids automated collection; request an export via admins.",
    "www.facebook.com": "Meta ToS forbids automated collection; request an export via admins.",
    "m.facebook.com": "Meta ToS forbids automated collection; request an export via admins.",
    "web.facebook.com": "Meta ToS forbids automated collection; request an export via admins.",
}


class ScrapeRefused(RuntimeError):
    """Raised when a fetch is blocked by governance rules, not by the network."""


@dataclass
class FetchResult:
    """One fetched resource, already persisted under data/raw/."""

    url: str
    path: Path
    sha256: str
    content_type: str
    from_cache: bool
    fetched_at: str
    status_code: int | None = None


@dataclass
class PoliteFetcher:
    """Rate-limited, robots-aware, content-addressed HTTP client.

    Parameters
    ----------
    source_id:
        Short slug identifying the scraper (e.g. ``"cainta_ordinances"``).
        Fetched files land in ``data/raw/<source_id>/``.
    respect_robots:
        Leave this True. It exists as a parameter only so a caller can be
        explicit when a source publishes a machine-readable licence that
        supersedes robots.txt -- and so that choice shows up in a diff.
    """

    source_id: str
    respect_robots: bool = True
    min_delay: float = MIN_DELAY_SECONDS
    session: requests.Session = field(default_factory=requests.Session)
    _last_request_at: dict[str, float] = field(default_factory=dict, repr=False)
    _robots: dict[str, urllib.robotparser.RobotFileParser | None] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.out_dir.mkdir(parents=True, exist_ok=True)

    @property
    def out_dir(self) -> Path:
        return RAW_DIR / self.source_id

    # -- governance ------------------------------------------------------

    def _check_denylist(self, url: str) -> None:
        host = urlparse(url).netloc.lower()
        if host in DENYLIST:
            raise ScrapeRefused(f"{host} is on the denylist: {DENYLIST[host]}")

    def _robots_for(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(f"{origin}/robots.txt")
            try:
                parser.read()
            except Exception:
                # A missing or unreachable robots.txt is not permission to
                # hammer the host, but it is not a prohibition either. Record
                # None and fall through to the rate limiter.
                parser = None
            self._robots[origin] = parser
        return self._robots[origin]

    def allowed(self, url: str) -> bool:
        """True if robots.txt permits our User-Agent to fetch ``url``."""
        if not self.respect_robots:
            return True
        parser = self._robots_for(url)
        if parser is None:
            return True
        return parser.can_fetch(USER_AGENT, url)

    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_request_at.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)
        self._last_request_at[host] = time.monotonic()

    # -- fetching --------------------------------------------------------

    def fetch(self, url: str, filename: str | None = None) -> FetchResult:
        """Download ``url`` into data/raw/<source_id>/ unless already cached.

        Caching is by target filename: if the file exists we do not issue the
        request at all. Government PDFs change annually at most, and a
        re-scrape that hits the network to confirm "unchanged" is still a
        request we promised not to make.
        """
        self._check_denylist(url)
        if not self.allowed(url):
            raise ScrapeRefused(f"robots.txt disallows {url} for {USER_AGENT}")

        target = self.out_dir / (filename or _filename_for(url))
        if target.exists():
            digest = sha256_file(target)
            return FetchResult(
                url=url,
                path=target,
                sha256=digest,
                content_type=_guess_type(target),
                from_cache=True,
                fetched_at=datetime.fromtimestamp(
                    target.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            )

        self._throttle(url)
        response = self.session.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()

        target.write_bytes(response.content)
        digest = hashlib.sha256(response.content).hexdigest()
        result = FetchResult(
            url=url,
            path=target,
            sha256=digest,
            content_type=response.headers.get("Content-Type", "unknown"),
            from_cache=False,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status_code=response.status_code,
        )
        self._record(result)
        return result

    def get_text(self, url: str) -> str:
        """Fetch and return decoded text without persisting a copy.

        Used for index pages we parse for links but do not need to archive.
        """
        self._check_denylist(url)
        if not self.allowed(url):
            raise ScrapeRefused(f"robots.txt disallows {url} for {USER_AGENT}")
        self._throttle(url)
        response = self.session.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text

    # -- provenance ------------------------------------------------------

    def _record(self, result: FetchResult) -> None:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "source_id": self.source_id,
            "url": result.url,
            "path": str(result.path.relative_to(REPO_ROOT)),
            "sha256": result.sha256,
            "content_type": result.content_type,
            "fetched_at": result.fetched_at,
            "status_code": result.status_code,
        }
        with MANIFEST_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _filename_for(url: str) -> str:
    """Derive a stable, filesystem-safe name from a URL.

    Wix asset paths (/_files/ugd/<hash>.pdf) carry no human-readable name, so
    the URL hash is prefixed to keep collisions impossible while leaving the
    original basename visible.
    """
    parsed = urlparse(url)
    basename = Path(parsed.path).name or "index"
    stem = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in basename)
    return f"{stem}_{safe}"


def _guess_type(path: Path) -> str:
    return {
        ".pdf": "application/pdf",
        ".json": "application/json",
        ".html": "text/html",
        ".csv": "text/csv",
    }.get(path.suffix.lower(), "application/octet-stream")


def write_interim(source_id: str, name: str, payload: object) -> Path:
    """Write a parsed, structured artefact to data/interim/<source_id>/."""
    out_dir = REPO_ROOT / "data" / "interim" / source_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path
