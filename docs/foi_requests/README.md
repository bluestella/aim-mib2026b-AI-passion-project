# FOI Requests

Phase 0 of the plan (§3.1). Three requests, filed in week 1, no warm contact required.

Under **Executive Order No. 2, s. 2016**, any Filipino can request records from
executive-branch agencies. NSWMC is a listed agency with an active request queue, and
waste-data requests for theses and feasibility studies are routine.

## The three requests

| ID | Agency | Channel | Draft |
|---|---|---|---|
| A | NSWMC (National Solid Waste Management Commission) | eFOI — `foi.gov.ph/agencies/nswmc/` | [`request_A_nswmc.md`](request_A_nswmc.md) |
| B | DENR-EMB Region IV-A (CALABARZON) | eFOI | [`request_B_emb_r4a.md`](request_B_emb_r4a.md) |
| C | Cainta MENRO | Email / paper, under the LGU's own FOI ordinance | [`request_C_cainta_menro.md`](request_C_cainta_menro.md) |

## The clock

EO 2 s. 2016 gives an agency **15 working days** to respond, extendable **once by 20
more** where the request needs extensive search or examination. `foi_tracker.py`
computes both dates:

```bash
python -m scrapers.foi_tracker add --id A --agency "NSWMC" \
    --subject "Cainta SCMAR + 10-Year SWM Plan" --filed 2026-08-03
python -m scrapers.foi_tracker status
```

The tracker does not model Philippine holidays — they are proclaimed annually and
would need their own source — so its due dates run slightly early. That is the safe
direction for a reminder.

## Expectations

The plan budgets **15–30 working days** and assumes roughly a **50% substantive hit
rate**. File all three. One partial response transforms the project; zero responses
costs nothing, because Phases 2–3 do not depend on FOI.

The paper trail is itself the point. A citizen arriving at the MENRO with a filed
request and a working prototype is a very different visitor from one arriving with a
pitch deck.

## When a response arrives

1. Save the attachment under `data/raw/foi/<request_id>/` unmodified.
2. Log it: `python -m scrapers.foi_tracker update --id A --status responded --outcome "..."`.
3. If it contains ordinance text or MRF locations, update
   `rules/cainta_disposal_rules.yaml` and flip the relevant `verification` field to
   `harvested` with a `retrieved_on` date.
4. Re-run `python -m daloy.rules_engine --audit` to confirm the Phase-1 gate moved.

## If a request is denied

A denial must cite a specific exception. Note it in the log's `outcome` column and
consider an appeal to the agency head, which EO 2 provides for. Do not re-file the
same request — refine it and narrow the scope instead.
