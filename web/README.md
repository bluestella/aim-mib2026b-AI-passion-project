# web/ — the PWA

**Phase 3: rules-only v1.** Next.js 16 (App Router) + React 19 + TypeScript, deployable
to Vercel with no configuration beyond a root directory.

A mobile-first PWA — no install, no camera, **no machine learning**. The user picks a
material by its junkshop trade name and gets the Pathway Card plus the Flow Simulation.
That sequencing is deliberate (plan §9): if Phases 4–6 never happen, Cainta still gets
the first machine-readable map of where its waste actually goes.

---

## Deploy to Vercel

The repository root is a Python project, so Vercel must be told where the app lives.

1. Import the repository at [vercel.com/new](https://vercel.com/new).
2. **Set Root Directory to `web`.** This is the only required setting — it is a Vercel
   project setting, not something `vercel.json` can express.
3. Framework preset auto-detects as Next.js. Build command, output directory and
   install command all take their defaults.
4. Deploy. There are no environment variables and no secrets: the app has no backend,
   no API keys, and no analytics.

Or from the CLI:

```bash
npm i -g vercel
cd web && vercel
```

All four routes prerender as static content, so this runs on Vercel's free tier and
serves entirely from the edge.

## Develop

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

If you change anything under `rules/`, recompile the data bundle from the repo root:

```bash
python scripts/build_app_data.py     # -> web/src/data/rules.json
```

`pytest` fails if the committed bundle drifts from the YAML, so a rules change that
never reached the app gets caught rather than silently shipping stale guidance.

## Verify

```bash
npm run verify       # typecheck + lint + build
```

and, against the production build:

```bash
npm run build && npx next start -p 8765 &
python scripts/drive_app.py --screenshots ./shots
```

The browser drive walks all ten screens and asserts the invariants below. Run it
against `next start`, not `next dev` — dev mode skips the service worker and is not
what Vercel ships.

---

## Four invariants

Asserted by `scripts/drive_app.py`, not merely intended.

**1. Nothing is attributed to the municipality while unverified.** Cards gate on
`presentable_as_official`, which is `false` for all 11 materials today. They read
*"Kaugnay na batas"* (related law) with an explicit line that this is not an official
LGU statement — never *"Batay sa"* (based on). Plan §7.8.

**2. No location is requested or stored.** There is no geolocation call anywhere in
this app. The barangay picker is the whole location model and never leaves
`localStorage`. Plan §7.5 asked for coordinates to be binned before storage; v1 goes
further by never obtaining one.

**3. Prices are never presented as what a shop will pay.** Every price carries the
unverified caveat while `verified_shops` is 0, the Bote Bank totals **grams rather
than pesos**, and glass — nominal price, usually refused — shows *"Madalas
tinatanggihan"* instead of a green price tag.

**4. The flow diagram is labelled schematic.** A staged diagram of the documented
drainage direction, never drawn over a basemap, because a stylised line on a map reads
as surveyed truth. No creek is named, because which creek serves which barangay is
unverified.

---

## Architecture

```
src/
  app/
    layout.tsx           Shell: store provider, top bar, provisional banner, tabs
    page.tsx             The scan wizard (steps, not routes — see below)
    bote-bank/page.tsx   Local ledger
    junkshop/page.tsx    Server component; honest empty state
    privacy/page.tsx     Server component; readable with JS disabled
    globals.css          One token set, light and dark
  components/            Presentational; no data fetching
  lib/
    types.ts             The contract with scripts/build_app_data.py
    rules.ts             Bundle access + `resolve()`, mirroring daloy.rules_engine
    store.tsx            localStorage via useSyncExternalStore
    useReducedMotion.ts  matchMedia via useSyncExternalStore
  data/rules.json        Generated. Do not edit.
public/
  sw.js                  Runtime cache; not precache — Next hashes asset names
  manifest.webmanifest, icon.svg
```

**Tabs are routes, the wizard is not.** `/`, `/bote-bank`, `/junkshop` and `/privacy`
are independent destinations and deserve URLs. The scan sequence — pick a thing,
describe it, see the answer — is one decision; giving each step a URL would invite
someone to land on a card with no selection, a state with no meaning.

**The bundle is imported, not fetched.** It is a build-time artefact, so bundling it
means no loading state, no fetch-failure path, and no chance of rendering before its
own data arrives. `lib/types.ts` is the contract: if the Python renames a field,
`tsc --noEmit` fails here rather than the UI rendering `undefined` at a user.

**External state is read through `useSyncExternalStore`.** localStorage and
`matchMedia` are both external stores. Copying them into React state inside an effect
renders once empty and again correct — which is precisely the flash of the setup
screen a returning user should never see.

**Plain CSS with custom properties.** No Tailwind, no CSS Modules. The design is one
small token set and eight screens; a utility framework would add a dependency and a
build concept without removing a line of thinking.

---

## Differences from the plan, and from the vanilla build

**React, as plan §8 specifies.** The previous build was vanilla JS because v1 has no
ML and needed no framework. Moving to Next.js buys three things that mattered more
than that simplicity: TypeScript checking of the generated bundle, server-rendered
privacy and junkshop pages that are readable with JavaScript disabled, and the
deployment target the user asked for. TF.js joins this stack in Phase 6.

**Two structural bugs from the vanilla build cannot recur here.** The flow animation's
timers are owned by an effect that React tears down, rather than scheduled from a
click handler that a subsequent navigation cancelled. Modifier checkbox state is
derived from the selection on every render, rather than held separately and allowed to
desync.

**The service worker is a runtime cache, not a precache.** Next content-hashes asset
filenames, so there is no fixed list to enumerate. `/_next/static/*` is cache-first
(the hash *is* the version); navigations are network-first with a cache fallback. The
rules bundle needs no special case any more — it is versioned by the same content hash
as the code that reads it, so a stale bundle can no longer pair with fresh code.

---

## What v1 does not do

- **No camera, no classifier.** Phases 4–6.
- **No junkshop locations.** Phase 2 fieldwork. The screen says so plainly rather than
  showing an empty map that implies Cainta has no junkshops.
- **No collection schedules.** Blocked on FOI request C — and per plan §11 this is
  probably the strongest recurring-value feature the app could carry.
- **No accounts, no backend, no student features.** The school channel needs
  school-mediated parental consent and legal review before a single minor uses this.

## Before a student uses this

Parental consent flow, school-mediated. No public profiles for minors. Class-level
leaderboards only — never individual children. See
[../docs/privacy_notice_tl.md](../docs/privacy_notice_tl.md), which still needs legal
review.
