# Reliability, outage cost and Massachusetts C&I customers: research for the v3 model

MIT Energy & Climate Hack 2026 · REON challenge · Nov 7, 2026, evening (sources audited 6 pm: weak and vendor sources removed or labelled; Eversource rates checked against Eversource's own summary)

Why this file exists: after meeting Tim Ren (REON CTO), we are adding the single-point-of-failure effect to the model. In a conventional series string one failed cell stops every cell; REON keeps about 10% of the cells as backups and switches a failed cell out. This file gathers the public data behind the new inputs and the customer context. Every number has a source in the table at the end (R1–R20); where no good public number exists we say so and give a range.

---

## 1. What Tim told us (Nov 7, in person and Discord)

| Topic | What he said | How we use it |
|---|---|---|
| String size | 200–300 cells in series in one string | 250 cells per 60 kWh block |
| Redundancy | About 90% of cells in use and 10% redundant backups; switches rotate cells, they do not bypass permanently | Headroom k = 10% of the string (25 of 250) |
| Cell voltage | 2.5–3.6 V for their sodium cells (vs 3.0–4.2 V lithium), set by the chemistry | Voltage floor 2.5 V already used for βpower |
| Cells | 20,000-cycle NFPP sodium cells; industry warranty 10 years / 8,000 cycles | Our aging is pessimistic for these cells (upside) |
| Sensing | Within 5%, often much better; voltage and temperature (terminal and body) per cell, up to 100 Hz | 5% sensing barely changes the result |
| Switch loss | "Very minimum overhead, but not none", depends on switch impedance | Kept at 0.5%; 1 mΩ switches would erase the gain (sensitivity) |
| 2–3× | REON's own comparison of its system against a weakest-link base system | Our model reproduces this only when the base system is lost at its first cell failure (Section 3) |
| Single point of failure | Reliability of a series string falls as (0.999)^N | New: failures handled the way a real base system experiences them |
| Customers | C&I, not residential; 60 kW is what customers prefer now; suburban sites, small businesses that value energy density; they care about cycle life, round-trip efficiency and depth of discharge | Customer view of the dashboard leads with these |
| Mission | Power accessible; new technology into legacy systems; chemistry- and cell-agnostic | Pitch framing |

## 2. How often does a cell fail? No good public number exists, so we bracket it

A hard cell failure here means the cell can no longer carry the string current safely (open circuit, internal short, runaway self-discharge), not gradual capacity fade, which the aging model already covers.

| Evidence | What it says | Per-cell rate it implies |
|---|---|---|
| Series reliability formula (patent DE/US, Bosch-style) [R1] | A 100-cell string with 100 ppm per cell fails 9.95% of the time; a string fails about N times as often as one cell | 100 ppm per period, used as an illustration |
| Second battery-pack patent [R2] | "A battery pack using 48 cells of 0.1% in failure rate will have a total failure rate of 4.8%" | 0.1%, illustrative |
| Tim Ren, in person | (1 − 0.999)^N | 0.1% per cell per year, illustrative |
| EV packs, Recurrent (about 15,000 vehicles) [R3, R4] | Battery replacements due to failure, outside recalls: 1.5% overall; well under 1% for model years 2016–2023; 0.3% for 2022 and later | Packs hold about 100 series elements, so well under 1% over about 5 years is roughly 10–20 ppm per element per year. An upper bound for modern cells, since it also counts capacity replacements |
| CATL manufacturing target [R5] | No more than 1 defect per billion cells (internal target, not audited field data) | Far below 1 ppm at manufacture |
| EPRI BESS failure database, Oct 2026 [R6–R8] | Large thermal events (fire, explosion, arc flash) at 0.04–0.14% per unit per year; 0.04 failures per GWh in 2025; failures fell 98% since 2018 | System-level fires only, not cell failures, so not usable as a per-cell rate |

**Model inputs:** 10 ppm, 100 ppm and 1,000 ppm (0.1%) per cell per year, with 100 ppm as the central case. Faults are homogeneous across cells (the same rate for every cell) so the result does not depend on our placeholder risk factors. A 250-cell fixed string then fails:

| Per-cell rate | Fixed string, per year | Fixed string, over 10 years | REON (25 backups), over 10 years |
|---|---|---|---|
| 10 ppm | 0.25% | 2.5% | effectively 0 |
| 100 ppm | 2.5% | 22% | effectively 0 |
| 1,000 ppm (Tim's example) | 22% | 92% | effectively 0 (expected 2.5 failures against 25 backups) |

(1 − (1 − r)^250 per year; Poisson for REON. These are exact arithmetic on the assumed rate.)

## 3. What a cell failure costs a conventional string

Two cases bracket reality, and the model now runs both:

- **Repair:** the string is off until a technician replaces the failed cell or module. Our default outage is 14 days (assumed; parts lead time dominates). A truck roll costs "$250 or more for transportation and hours alone" for solar inverters [R9]; a battery module swap needs a qualified crew and parts, so we assume **$1,500 per visit** (placeholder; show $500–3,000). Replacing one module in an aged string also leaves a new, mismatched cell in an old string [R10].
- **Retire:** the owner replaces the whole block at the first failure (for example, out of warranty, parts no longer available, or the repair does not pay). This is the worst case for the base system and the case behind REON's 2–3×.

## 4. Massachusetts grid reliability and outage cost

- **Massachusetts is reliable by US standards.** EIA 2025: the average customer saw 121 minutes of outage over 0.906 interruptions (133.6 minutes each) including major events; 75 minutes and 0.74 interruptions without them. US average: 262.6 minutes, 1.34 interruptions [R11]. So backup power is worth less in Massachusetts than in the Southeast, and the case leans on bill savings.
- **Outage cost to businesses.** LBNL's updated Interruption Cost Estimate model (ICE 2.0, Phase 1 report 2025; surveys 2022–2024 in 24 mostly Eastern and Midwestern utility territories) gives an average non-residential cost per event, in 2023 dollars, of $609 for a momentary interruption, $2,839 for 2 hours, $6,172 for 8 hours and $12,646 for 24 hours (ES Table 3) [R13]. The report combines small, medium and large businesses in one model, so a small grocer's cost is likely below these averages and a cold store's above. At Massachusetts' 0.9 interruptions a year of about 2 hours each, that is roughly $2,500 a year for an average business (our arithmetic). LBNL's free online calculator gives a site-specific number.
- Dropped in this audit: a single national ORNL figure ($6,031 per C&I customer in 2024) whose basis (per outage or per year) the press release does not state; generator-vendor "lost sales per hour" figures; and a one-store anecdote from Colorado.
- **Massachusetts funds resilience.** DOER's Advancing Massachusetts Power program awarded more than $40 million to 36 projects on Sep 18, 2026, including behind-the-meter storage for backup at critical facilities [R17]. This is a possible co-funding route for REON systems at community sites.

## 5. Customers that fit: cold storage and small businesses

**Cold storage (for example Americold).**
- Americold's own site lists Massachusetts warehouses in Gloucester (Rogers St. and Rowe Square), Taunton and Middleborough [R22]. When Middleborough opened in 2018 (built for Ocean Spray), Americold had five Massachusetts sites including Boston, almost 19 million cubic feet in total [R18]; we have not confirmed that the Boston site still operates.
- Americold sites already took part in an Eversource demand-management program using thermal storage from Viking Cold, alongside Sysco and the Greater Boston Food Bank [R19]. Massachusetts cold-storage operators are therefore already paying to cut peaks.
- Demand charges are often quoted as 30–50% of a cold-storage bill, with refrigeration compressors using 70–80% of the electricity (vendor blog citing others; indicative only) [R20].
- Americold says its buildings hold temperature for up to a week without power [R21], so for them the value is demand charges and grid programs, not backup.
- Size: a large cold store peaks at hundreds of kW, so it would use several EBS blocks; our 2-block site is closer to a small cold store, food distributor or grocery.

**Small businesses ("mom and pop").** Tim pointed to suburban sites where space matters. Convenience stores, restaurants and small grocers have refrigeration loads (spoilage risk in outages) and pay demand charges on G-2-type rates. These are the sites a 60 kW / 120 kWh system fits.

## 5b. Which Eversource rate each customer pays (checked against Eversource's own summary)

Eversource's 2026 Summary of Eastern Massachusetts Electric Rates, effective Sep 1, 2026 [R23], per kW of monthly peak demand:

| Rate | Who | Distribution + transmission demand charge |
|---|---|---|
| G-1, demand price option | Small businesses averaging up to 100 kW (charged on kW above 10 kW) | $22.31 + $19.34 = **$41.65/kW** |
| **G-2 (our default)** | Medium general service | $20.21 + $13.74 = **$33.95/kW** (confirmed) |
| G-3 | Large general service (large cold stores) | $15.97 + $14.08 = **$30.05/kW** (plus an optional coincident-peak transmission charge) |

So a small grocer on G-1's demand option would see a higher value per kW than our default, and a large cold store on G-3 slightly lower.

## 6. What changes in the model (v3)

1. **Pack:** 250 cells per string, k = 25 (10% backups), same cells in both designs. As we read Tim's "discount at a power cell, not the energy cell": with rotation, every cell still gives its energy; only the number of cells in the string at any moment (and so voltage and power) is reduced.
2. **Cell failures:** homogeneous rate per cell, 0 / 10 / 100 / 1,000 ppm per year.
3. **Base system response to a failure:** repair (14-day outage, $1,500 visit) or retire the block.
4. **REON response:** switch out the failed cell; a visit only when more than 25 cells are out.
5. **Economics:** service-visit cost added; outage cost reported as context (Section 4), not added to NPV.

---

## Sources

| # | Source | Link |
|---|---|---|
| R1 | US patent 9,041,341, "More readily available traction battery" (series failure-rate formula, 100 ppm example) | https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9041341 |
| R2 | US patent 6,420,852, "Battery pack" (48 cells at 0.1%) | https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6420852 |
| R3 | US DOE Fact of the Week #1339 (Recurrent: 1.5% replacements outside recalls) | https://www.energy.gov/cmei/vehicles/articles/fotw-1339-april-22-2024-plug-electric-vehicle-battery-replacements-due |
| R4 | InsideEVs on Recurrent replacement rates by generation (0.3% for 2022+) | https://insideevs.com/news/779210/ev-battery-replacements-data-tesla/ |
| R5 | CarNewsChina, CATL 1-ppb defect target (Sep 2026) | https://carnewschina.com/2026/09/04/china-is-launching-nearly-3-new-evs-a-day-catl-warns-of-batch-battery-failures/ |
| R6 | EPRI, Risk Factors and Failure Statistics of Lithium-Ion BESS (Oct 2026) | https://restservice.epri.com/publicdownload/000000003002034920/0/Product |
| R7 | Utility Dive on the EPRI report (0.04–0.14% per year) | https://www.utilitydive.com/news/battery-system-failures-fell-98-in-7-years-but-older-systems-need-special/832882/ |
| R8 | pv magazine USA on the EPRI report (0.04 per GWh in 2025) | https://pv-magazine-usa.com/2026/10/14/battery-energy-storage-failures-are-down-98-since-2018-and-continue-to-decline/ |
| R9 | Fronius, value of field serviceability (truck roll $250+; 2021 solar-inverter vendor blog, context only) | https://fronius.com/en-us/usa/solar-energy/installers-partners/info-center/blog/the-value-of-field-serviceability-12-17-2021 |
| R10 | US patent 12,015,171 (module replacement and balancing in an aged pack) | https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12015171 |
| R11 | EIA Electric Power Annual, Table 11.3, reliability by state (2025, 2024) | https://www.eia.gov/electricity/annual/html/epa_11_03.html |
| R12 | (dropped in audit) | — |
| R13 | LBNL, ICE Calculator 2.0 Phase 1 final report (2025), ES Table 3 | https://www.osti.gov/servlets/purl/2569414 |
| R14 | LBNL, ICE 2.0 survey basis (24 territories, 2022–2024) | https://eta-publications.lbl.gov/bibcite/export/bibtex/bibcite_reference/36587 |
| R15 | (dropped in audit) | — |
| R16 | (dropped in audit) | — |
| R17 | Mass.gov, AMP energy storage grants, Sep 18, 2026 | https://www.mass.gov/news/healey-driscoll-administration-awards-more-than-40-million-to-power-critical-facilities-during-outages |
| R18 | Fleet Owner, Americold Middleborough opening (five MA sites) | https://fleetowner.com/refrigerated-transporter/cold-storage-logistics/article/21231791/americold-ocean-spray-open-new-facility-in-middleborough-ma |
| R19 | RefIndustry, Viking Cold / Eversource project (Americold, Sysco, Greater Boston Food Bank) | https://refindustry.com/news/cold-chain/viking-cold-named-platinum-winner-of-cleanie-award-s-project-of-the-year/whatsapp:/send |
| R20 | Envigilance, cold storage demand charges (vendor blog citing Inertia Resources, EIA CBECS; indicative) | https://envigilance.com/blog/cold-storage-demand-charges/ |
| R21 | FreightWaves, Americold's outage resilience | https://www.freightwaves.com/news/americolds-secret-to-surviving-power-outages |
| R22 | Americold, Gloucester (Rogers St.) facility page, listing nearby Massachusetts sites | https://www.americold.com/gloucester-rogers-st-ma-americold-logistics-gloucester-ma/ |
| R23 | Eversource, 2026 Summary of Eastern Massachusetts Electric Rates (effective Sep 1, 2026) | https://www.eversource.com/docs/default-source/rates-tariffs/ema-greater-boston-rates.pdf?sfvrsn=c27ef362_36 |
| — | Tim Ren (REON CTO), in person and hack Discord, Nov 7, 2026 | Not public |
