# FOI Request C — Cainta MENRO

| | |
|---|---|
| **Agency** | Municipal Environment and Natural Resources Office (MENRO), Municipality of Cainta |
| **Channel** | Email or paper — LGUs operate under their own FOI ordinance, not the eFOI portal |
| **Status** | Draft — not yet filed |
| **Purpose** | Collection schedules, hauling volumes, MRF locations |

---

## Before filing

LGUs are **not** covered by EO 2 s. 2016, which binds the executive branch. Local FOI
runs on each LGU's own ordinance or on the Local Government Code's transparency
provisions. So:

1. Confirm the MENRO's officer, address, and email from
   `cainta.gov.ph/departments-and-offices` — `scrapers/cainta_ordinances.py` harvests
   that page.
2. Check whether Cainta has enacted a local FOI ordinance. If it has, cite it. If it
   has not, cite the Local Government Code's provisions on public records and the
   general policy of full public disclosure.
3. Address it to the Municipal Mayor's Office **through** the MENRO if the ordinance
   requires it. Getting the addressee wrong is the most common reason a local request
   stalls.

## Subject

Request for solid waste collection and facility records, Municipality of Cainta

## Request body

> Dear [Officer name], Municipal Environment and Natural Resources Officer,
>
> I am a resident/researcher requesting access to the following public records of the
> Municipality of Cainta concerning solid waste management:
>
> 1. **Collection routes and schedules by barangay** — the days on which biodegradable,
>    recyclable, and residual waste are collected in each of the seven barangays.
>
> 2. **Locations of operating Materials Recovery Facilities**, by barangay, and the
>    materials each accepts.
>
> 3. **Waste volumes hauled** under the municipality's current hauling contract or
>    arrangement, for the most recent 12 months available, in tonnes per month.
>
> 4. A copy of **Municipal Ordinance No. 2023-012** (Environmental Protection and Waste
>    Management Code of 2023) and **Ordinance No. 2022-010**, if these are not already
>    posted on the municipal website.
>
> **Purpose.** I am developing a free, non-commercial web application that answers a
> simple question for Cainta residents: for a given item of household waste, where does
> it go, and is there anywhere nearby that will take it? The collection schedule is the
> single most useful piece of information the application can carry, and residents
> currently have no reliable way to look it up.
>
> The application is designed to support compliance with RA 9003 and with the
> municipality's own ordinances. It is not an assessment of the municipality's
> performance. I would welcome the opportunity to show the MENRO a working prototype
> and to correct anything it gets wrong before any public release.
>
> I am happy to collect copies in person or to cover reasonable reproduction costs.
>
> Respectfully,
> [Name, address, contact]

## Why this request matters most of the three

Items 1 and 2 are the only records in the whole FOI set that a resident uses *weekly*.
Plan §11 asks what makes someone open the app a second time — a correct, current
collection schedule is a stronger answer than the Pathway Card, and it can only come
from here.

## Notes on approach

The plan (§10) flags a real risk: an LGU can read a public map of leakage hotspots as a
public map of its own failures. The framing above is deliberate — a compliance support
tool, offered for correction before release, not an audit.

The offer to demonstrate a prototype is the actual point of this request. File Requests
A and B first; arriving with a filed eFOI paper trail and something working changes the
conversation.

## Expected outcome

| Outcome | Probability | What it unlocks |
|---|---|---|
| Collection schedules received | Medium | The strongest recurring-value feature in the app |
| Ordinance copies received | Medium–high | Flips `verification: harvested` in the rules table — the Phase-1 gate |
| Meeting offered | Medium | The partnership the plan's Phase 7 depends on |
| No response | Medium | Fall back to the published ordinance PDFs and the field survey |
