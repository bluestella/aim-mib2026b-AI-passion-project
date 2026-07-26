"""Track FOI request status and statutory deadlines (plan §3.1).

Not a scraper -- eFOI has no public API for a requester's own queue, and the
plan explicitly budgets 15-30 working days for responses. What actually needs
automating is the *clock*: EO 2 s. 2016 gives an agency 15 working days to
respond, extendable once by a further 20 working days. Missing that date is
the difference between a follow-up you can point at a rule for and a follow-up
that sounds like nagging.

The log lives at docs/foi_requests/foi_log.csv and is meant to be edited by
hand as well as by this tool. It is deliberately a CSV in the docs tree, not a
database: the paper trail is itself a credential when the MENRO conversation
finally happens (plan §3.1).

Run:
    python -m scrapers.foi_tracker status
    python -m scrapers.foi_tracker add --id D --agency "LLDA" --subject "..." --filed 2026-08-03
    python -m scrapers.foi_tracker update --id A --status responded --notes "SCMAR CY2023 received"
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from scrapers.common import REPO_ROOT

LOG_PATH = REPO_ROOT / "docs" / "foi_requests" / "foi_log.csv"

FIELDNAMES = (
    "request_id",
    "agency",
    "subject",
    "filed_on",
    "channel",
    "status",
    "responded_on",
    "outcome",
    "notes",
)

VALID_STATUS = ("draft", "filed", "acknowledged", "extended", "responded", "denied", "lapsed")

#: EO 2 s. 2016 response clock, in working days.
RESPONSE_WORKING_DAYS = 15
EXTENSION_WORKING_DAYS = 20


@dataclass
class Deadline:
    due_on: date
    working_days_remaining: int
    overdue: bool


def add_working_days(start: date, working_days: int) -> date:
    """Advance ``start`` by N working days, skipping weekends.

    Philippine regular and special non-working holidays are *not* modelled --
    they are proclaimed annually and would need their own data source. This
    therefore returns a date that is at worst slightly early, which is the safe
    direction for a follow-up reminder.
    """
    current = start
    remaining = working_days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def working_days_between(start: date, end: date) -> int:
    """Count working days from ``start`` to ``end`` (negative if end precedes start)."""
    if end < start:
        return -working_days_between(end, start)
    days = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days += 1
    return days


def deadline_for(filed_on: date, extended: bool = False, today: date | None = None) -> Deadline:
    budget = RESPONSE_WORKING_DAYS + (EXTENSION_WORKING_DAYS if extended else 0)
    due = add_working_days(filed_on, budget)
    now = today or date.today()
    remaining = working_days_between(now, due)
    return Deadline(due_on=due, working_days_remaining=remaining, overdue=due < now)


def load() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("request_id")]


def save(rows: list[dict]) -> Path:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in FIELDNAMES})
    return LOG_PATH


def cmd_status(_: argparse.Namespace) -> None:
    rows = load()
    if not rows:
        print(f"No FOI requests logged yet. Expected file: {LOG_PATH}")
        print("Phase 0 of the plan requires three requests filed in week 1 (§3.1).")
        return

    print(f"{'ID':<4} {'AGENCY':<28} {'STATUS':<13} {'FILED':<11} {'DUE':<11} CLOCK")
    open_count = 0
    for row in rows:
        filed_raw = (row.get("filed_on") or "").strip()
        status = (row.get("status") or "").strip() or "draft"
        if not filed_raw:
            clock = "not filed"
            due_text = "-"
        else:
            filed_on = date.fromisoformat(filed_raw)
            deadline = deadline_for(filed_on, extended=(status == "extended"))
            due_text = deadline.due_on.isoformat()
            if status in ("responded", "denied"):
                clock = "closed"
            elif deadline.overdue:
                clock = f"OVERDUE by {-deadline.working_days_remaining} wd"
                open_count += 1
            else:
                clock = f"{deadline.working_days_remaining} wd left"
                open_count += 1
        print(
            f"{row['request_id']:<4} {row.get('agency', '')[:27]:<28} "
            f"{status:<13} {filed_raw or '-':<11} {due_text:<11} {clock}"
        )

    responded = sum(1 for r in rows if (r.get("status") or "") == "responded")
    print(
        f"\n{len(rows)} request(s) logged; {open_count} awaiting response; "
        f"{responded} responded."
    )
    print(
        "The plan assumes roughly a 50% substantive hit rate. Phases 2-3 do not\n"
        "depend on FOI -- if these all come back empty, the field survey is still\n"
        "the moat."
    )


def cmd_add(args: argparse.Namespace) -> None:
    rows = load()
    if any(r["request_id"] == args.id for r in rows):
        raise SystemExit(f"Request {args.id} already exists in {LOG_PATH}")
    rows.append(
        {
            "request_id": args.id,
            "agency": args.agency,
            "subject": args.subject,
            "filed_on": args.filed or "",
            "channel": args.channel,
            "status": "filed" if args.filed else "draft",
            "responded_on": "",
            "outcome": "",
            "notes": args.notes or "",
        }
    )
    save(rows)
    print(f"Added request {args.id} to {LOG_PATH.relative_to(REPO_ROOT)}")


def cmd_update(args: argparse.Namespace) -> None:
    rows = load()
    for row in rows:
        if row["request_id"] != args.id:
            continue
        if args.status:
            if args.status not in VALID_STATUS:
                raise SystemExit(f"status must be one of {VALID_STATUS}")
            row["status"] = args.status
            if args.status in ("responded", "denied"):
                row["responded_on"] = args.responded or date.today().isoformat()
        if args.outcome:
            row["outcome"] = args.outcome
        if args.notes:
            row["notes"] = args.notes
        save(rows)
        print(f"Updated request {args.id}")
        return
    raise SystemExit(f"No request {args.id} in {LOG_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show all requests and their statutory clocks.").set_defaults(
        func=cmd_status
    )

    add = sub.add_parser("add", help="Log a new FOI request.")
    add.add_argument("--id", required=True)
    add.add_argument("--agency", required=True)
    add.add_argument("--subject", required=True)
    add.add_argument("--filed", help="ISO date the request was filed.")
    add.add_argument("--channel", default="eFOI", help="eFOI, email, or paper.")
    add.add_argument("--notes", default="")
    add.set_defaults(func=cmd_add)

    update = sub.add_parser("update", help="Update the status of a logged request.")
    update.add_argument("--id", required=True)
    update.add_argument("--status", choices=VALID_STATUS)
    update.add_argument("--responded", help="ISO date of response.")
    update.add_argument("--outcome", default="")
    update.add_argument("--notes", default="")
    update.set_defaults(func=cmd_update)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
