# Junkshop Field Survey — Instrument

Phase 2 of the plan (§9). Target: 30–60 shops, two weekends. Gate to proceed: **≥25
verified**.

Plan §3 (Tier 4.4) is blunt about this: nothing else in the project is as valuable per
hour spent. OSM will not give you this — Philippine junkshops are systematically
under-mapped — and no government dataset contains it. This form is the moat.

---

## Before the first weekend: the five-shop test

Plan §11 raises a question that can kill the whole survey, so answer it before
committing two weekends:

> **Is the junkshop network actually willing to publish prices?** Price opacity may be
> their margin.

Visit **five** shops. Ask only Q7 (prices). If four or five refuse, stop and rethink —
the app falls back to a rules engine plus locations, and the price ticker that plan §11
identifies as the only durable reason to reopen the app is not available. Better to
learn that in one afternoon than after sixty visits.

---

## Script (Tagalog)

> Magandang [umaga/hapon po]. Estudyante po ako / gumagawa po ako ng libreng app para
> sa mga taga-Cainta — para malaman nila kung saan pwedeng dalhin ang mga bote, karton,
> at lata nila.
>
> Pwede po bang itanong kung anong mga materyales ang tinatanggap ninyo? Ilalagay po
> namin nang libre ang tindahan ninyo sa app, para may mas maraming makapunta rito.
>
> *(Kung tatanungin kung magkano ang bayad: Wala po, libre po. Wala rin po kaming
> kinikita sa app.)*

Lead with the listing, not the questionnaire. A free listing that brings them inbound
supply is a real offer, and it is why a busy shop owner should give you ten minutes.

---

## Form

### Identification

| # | Field | Type | Notes |
|---|---|---|---|
| 1 | Shop name | text | If unsigned, record "walang pangalan" and the nearest landmark |
| 2 | Barangay | one of 7 | |
| 3 | Street / landmark | text | |
| 4 | GPS coordinates | lat, lon | 5 decimal places. **Business premises — not personal data** |
| 5 | Photo of frontage | image | With permission. Confirms the shop exists and helps users recognise it |
| 6 | Contact number | text, optional | Ask if they want it listed. Many will |

### Commercial

| # | Field | Type | Notes |
|---|---|---|---|
| 7 | **Price per material** | PHP/kg | The core question — see table below |
| 8 | Materials accepted | multi-select | Use the 11-class taxonomy |
| 9 | Materials explicitly refused | multi-select | **As important as what they accept.** A user sent to a shop that refuses glass has been sent on a wasted trip |
| 10 | Minimum weight | kg, nullable | Common, and it silently makes a shop useless for a household with one bag |
| 11 | Accepts walk-in residents? | yes/no | **Critical.** Some buy only from established collectors. A no here means the shop should not appear in the app at all |
| 12 | Opening hours | text | OSM `opening_hours` syntax if you can |
| 13 | Open on Sunday? | yes/no | Asked separately because it is when most residents can actually go |

### Price table (fill per shop)

| Material | Trade name | PHP/kg | Refused? | Notes |
|---|---|---|---|---|
| `PET_bottle` | bote / plastik | | | Crushed vs. whole may price differently |
| `HDPE_PP_rigid` | sibak | | | |
| `plastic_film_sachet` | sachet | | | **Expect a refusal. Record it — a confirmed zero is a finding, not a blank** |
| `aluminium_can` | lata | | | |
| `ferrous_metal` | bakal / yero | | | |
| `copper_wire` | tanso | | | Ask about stripped vs. insulated |
| `glass_bottle` | bote (salamin) | | | Often refused; ask about refillables separately |
| `cardboard` | karton | | | Ask about the wet-weight deduction |
| `paper_newsprint` | dyaryo / puting papel | | | White paper usually grades higher |

### Context (ask if the conversation allows)

| # | Question | Why it matters |
|---|---|---|
| 14 | How often do prices change? | Sets the refresh cadence for the price ticker |
| 15 | Where does the material go next? | Traces the recovery chain past the shop — nobody has mapped this for Cainta |
| 16 | Do residents come directly, or mostly collectors? | Tells you whether the app's core assumption holds at all |
| 17 | Would you update your prices if we gave you a way to? | Tests the v2 junkshop role before building it |

### Survey metadata

| # | Field |
|---|---|
| 18 | Surveyor name |
| 19 | Date and time of visit |
| 20 | Owner consented to being listed? (yes/no) |
| 21 | Owner consented to price publication? (yes/no) |

**Both consent fields are required before a shop appears in the app.** A shop that
consents to a listing but not to prices gets listed without prices.

---

## After the survey

1. Enter into `data/processed/junkshops.csv` using the `junkshops` schema in
   [`data_dictionary.md`](data_dictionary.md).
2. Set `last_verified_date` and `price_updated_at` to the visit date. The UI shows both
   and decays confidence visibly as they age (plan §10).
3. Update `verified_shops` in `rules/cainta_disposal_rules.yaml` under
   `price_provenance`, then run `python -m daloy.rules_engine --audit` to confirm the
   Phase-2 gate.
4. **Contribute the locations back to OpenStreetMap** under ODbL (plan §7.7). Use
   `amenity=recycling` with `recycling:*` subtags — `shop=scrap_yard` is rare and
   poorly supported. This is both good citizenship and free permanent hosting for the
   part of the moat that is a public good.

Prices are yours; the locations belong on the commons.

---

## Field notes

- **Go on a weekday morning.** Shops are busiest when collectors arrive in the
  afternoon, and an owner mid-transaction has no time for you.
- **Bring printed copies.** Phone-only surveying looks like you are recording them.
- **Record refusals as data.** A shop that will not give prices is still a real
  location, and the refusal rate is the answer to plan §11's second question.
- **Never quote one shop's prices to another.** It is how you get thrown out of the
  second shop, and it turns a free listing into a competitive threat.
