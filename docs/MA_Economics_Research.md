# Massachusetts C&I storage: economics research for the REON model

MIT Energy & Climate Hack 2026 · researched Nov 7, 2026 · every number links to a source in the table at the end (`[S#]`).

**Confidence key:** **Official** = utility, state, IRS, NREL, ISO-NE document. **Trade press / analyst** = Energy-Storage.news, Modo, Utility Dive, law firms, Lazard. **Installer / aggregator** = marketing or data sites (NuWatt, EnergyBot, Nectar, Cleanview). Verify installer/aggregator figures against the official source before putting them on a slide.

---

## 0. What REON's CTO told the hack (Discord, Nov 6–7)

| Topic | What Tim Ren said | Use in our work |
|---|---|---|
| What the "tool" is | Not a new REON feature; "a dashboard for your presentation, to show your idea" | Our Cell Bypass Explorer fits exactly |
| BMS cost | About 3× a conventional BMS; a BMS is 2–3% of system cost; overhead "negligible compared to the cycle life gain" | Overhead input +4–6% of system cost; break-even line |
| Business model | EBS sold tech → product → customer; EPCs and channel partners "love it"; open to licensing / JV | EPCs as channel; owner as customer |
| Certification | UL testing underway, aiming for all certificates by end of 2026 | Say "UL testing underway", not "certified" |
| LCA | None for sodium; lithium data exists, only in person | Ask in person |
| Mixing packs | Can't manage another vendor's pack voltage, but can compensate its power drop to hold DC string voltage | Ask what this means for bypass headroom k |
| Chemistry | Building a chemistry-agnostic BMS/EMS; sodium product "far beyond prototyping"; keen to partner on mixed-use / chemistry-agnostic testing | Supports our spread multiplier and wider-spread (mixed-age) scenarios |
| Environmental metric | Both CO₂ avoided and material kept out of waste are welcome | Report both |
| Scope | One application in depth preferred over breadth | Massachusetts C&I only, done deeply |
| Audience | "End customer first" | Frame the dashboard for the asset owner |
| Cooling | EBS uses forced air (attached AC unit); passive cooling looks possible for sodium cells | Thermal context |
| Hot cells | A conventional BMS has one universal temperature limit; REON's can bypass a "hot" cell and let it rest | Resting is a real REON capability; add temperature-based resting |

---

## 1. Revenue streams for a C&I battery

### 1.1 ConnectedSolutions (Mass Save demand response) — strongest, most model-friendly

| Track | Rate | Events | Length / window | Notes | Source |
|---|---|---|---|---|---|
| Daily Dispatch | $200/kW-summer | 30–60 per summer | 2–3 h, 2–7 pm, Jun–Sep | 5-year incentive lock | [S1] Official |
| Targeted Dispatch | $35/kW-summer | 2–8 per summer | 3 h, 2–7 pm | | [S1] Official |
| Eversource Targeted Dispatch for Batteries | $100/kW-summer | 2–8 | 3 h | | [S1] Official |
| Eversource Winter Dispatch for Batteries | $50/kW-winter | 4–6 | 3 h | | [S1] Official |
| Eversource ConnectedSolutions+ pilot | $250–275/kW-summer | — | — | Ten named towns only | [S2] Installer, low confidence |

- **How it pays:** Daily Dispatch for batteries is paid on **average discharge (kW) across the event**. That equals our **firm kW** metric. [S1]
- Events are weekdays only, notified at 1 pm the day before. [S1]
- **Eligibility size, unresolved.** EnergyBot lists ≥50 kW [S3, aggregator]; the official PDF states no minimum [S1]. Rhode Island routes batteries ≤50 kW to the residential/small-business track [S4]. **If the 50 kW floor is real, a single 30 kW EBS is out; model the OES (60–120 kW) or several EBS.**
- The official PDF has no date or program year [S1]. Rhode Island plans a C&I performance factor for 2027–29 [S5], so rates may change.
- Enrollment is through approved curtailment service providers: CPower, Enel X, Voltus. [S6]

### 1.2 Clean Peak Standard (CPS) — paid per MWh discharged at peak

- ACP (price ceiling): **$45/MWh through 2025, $65/MWh for 2026–2032.** [S7] Official
- CPECs have historically cleared at about **87% of the $65 ceiling**, so about **$57/MWh** for the base case. [S8] Analyst
- Merchant batteries earn **1.0–2.0× multipliers**; contracted renewables only 0.01×. [S8]
- Rules are in flux: a May 28, 2026 emergency rule changed the 2026–2030 Minimum Standard and the near-term storage multiplier. [S9][S10] Official
- Municipal light plant territories are ineligible. [S11] Official
- **Model hook:** pays on MWh delivered in peak windows, so it scales with **lifetime energy**.
- **Stacking with ConnectedSolutions in the same hour: not confirmed.** Assume no double-count in the base case.

### 1.3 SMART 3.0 storage adder

- **Energy Storage Multiplier: $0.04 per kWh** of the paired solar's output (2026). [S12] Official
- Projects ≤25 kW no longer get the storage adder. [S13] Official
- Paid on solar kWh, so REON's cell control does not change it. Part of the stack, not a REON lever.

### 1.4 Demand charges (bill savings) — biggest stream, utility-dependent

| Utility / rate | Demand charge | Date | Source |
|---|---|---|---|
| Eversource Greater Boston G-2 | $18.53 distribution + $12.81 transmission ≈ **$31/kW-month** | 2024 | [S14] Official |
| Eversource Greater Boston G-2 | $20.21 + $13.74 = **$33.95/kW-month** | Eff. Sep 1, 2026 | Confirmed in Eversource's own 2026 Summary of Eastern MA Electric Rates (https://www.eversource.com/docs/default-source/rates-tariffs/ema-greater-boston-rates.pdf?sfvrsn=c27ef362_36); G-1 demand option $22.31 + $19.34 = $41.65; G-3 $15.97 + $14.08 = $30.05 |
| National Grid G-2 | **$15.06/kW-month** (transmission billed per kWh instead) | 2026 | [S15] Installer |

- G-2 bills on the greatest **15-minute peak** each month. [S16] Aggregator
- National Grid commercial Basic Service supply was about **21.7 ¢/kWh** (Jan 2026). [S16] Aggregator
- Machine-readable tariffs: OpenEI Utility Rate Database. [S17]
- **Decision:** model Eversource Greater Boston as base and National Grid as a sensitivity (about half the demand-charge value).

### 1.5 ISO-NE capacity market — expansion path, not base case

- ISO-NE filed to move to a **prompt (and later seasonal) auction** starting with the June 2028–May 2029 period. [S18] Analyst
- The last forward auction cleared **>1,800 MW of storage, ~6% of commitments**. [S19] Trade press
- ISO-NE's 2026 load forecast counts behind-the-meter batteries for the first time: **~111 MW installed** region-wide, **173 MW of additions** over 10 years, mostly in Massachusetts. [S20] Trade press

---

## 2. Policy landscape and market size

- **5 GW law (Section 83E):** utilities must contract ~5,000 MW of storage by July 31, 2030. [S21] Law firm
- **Round 1:** sought ~1,500 MW (Aug 2025), selected **1,268 MW**. [S22] Trade press
- **Round 2:** issued July 31, 2026, for **1,000 MW** plus a **250–300 MW distribution-connected carve-out**; bids were due Sept 9, 2026. [S22][S23] A possible future channel for REON's 2.5 MW / 5 MWh CES.
- **Installed base:** ~**742 MW** operating, ~**7,950 MW** planned (utility-scale, Sept 2026). [S24] Aggregator
- **Behind-the-meter** storage is still small: ~157 MW. [S25] Secondary, low confidence
- **Permitting:** a 2025 Land Court decision (Duxbury) reportedly made battery permitting clearer and more uniform. [S26] Secondary, verify

---

## 3. Federal tax credits and FEOC

- Storage projects that **begin construction by end of 2033** keep investment-tax-credit eligibility. [S27] Trade press
- **FEOC "material assistance" rules** apply to projects beginning construction on or after Jan 1, 2026. [S28] Law firm
- Required non-FEOC content for storage: **55% (2026), 60% (2027), 65% (2028), 70% (2029), 75% after**. [S29] Law firm
- IRS guidance: **Notice 2026-15**. [S30] Official
- **For REON:** if its sodium cells come from non-FEOC suppliers, customers keep the ITC. That is a possible edge over cheap imported LFP. **Ask Tim where cells are made.**

---

## 4. Cost benchmarks

| Benchmark | Value | Source |
|---|---|---|
| NREL ATB 2024 commercial battery pack price | 1 h: $211/kWh · 2 h: $215/kWh · 4 h: $199/kWh (pack only, not installed) | [S31] Official |
| NREL ATB 2025 commercial battery | Projections based on 4-hour cost synthesis | [S32] Official |
| Lazard 2025 LCOS, C&I standalone 1 MW / 2 h | **$319–506/MWh** | [S33] Analyst |
| Lazard 2025 LCOS, utility 100 MW / 4 h | $115–254/MWh | [S33] Analyst |
| Our installed-cost placeholder | $350/kWh | Placeholder, no official 2026 figure found |

---

## 5. Data for the model

| Need | Source |
|---|---|
| 15-minute commercial building load (MA warehouse, retail, school) | NREL ComStock end-use load profiles [S34][S35][S36] |
| Hourly solar for Boston | NREL PVWatts [S37] |
| Tariffs in code-readable form | OpenEI URDB [S17] |
| Event calendar | ConnectedSolutions: weekdays, 2–7 pm, Jun–Sep [S1] |
| Cell spread and knees | Zhou et al. 2026 public data [S38] |

---

## 6. Competitive landscape in Massachusetts

- **Distributed / municipal storage developers** (potential EPC or channel partners):
  - Lightshift: six new municipal projects, >23 MW. [S39]
  - Kearsarge: 104 MWh since 2019. [S40]
  - Solect (6 MW Norfolk project) and others. [S24]
  - Nexamp and BlueWave are also active. [S41]
- **Demand-response aggregators:** CPower, Enel X, Voltus. [S6] REON's EMS would work through one, or become one.
- **Imported competition:** Trina Storage supplied Lightshift's Massachusetts projects. [S42] Cheap, but FEOC rules now make imported systems riskier for tax credits.

---

## 7. How it plugs into the model

| Stream | Paid on | Model metric | Base value |
|---|---|---|---|
| ConnectedSolutions Daily Dispatch | Average kW over 2–3 h events | **Firm kW** | $200/kW-season |
| Demand charges (Eversource G-2) | Monthly 15-min peak kW | Firm kW + duration | ~$31–34/kW-month |
| Clean Peak (CPECs) | Peak-window MWh × multiplier | **Lifetime energy** | ~$57/MWh |
| SMART storage adder | Solar kWh | Not affected by REON | $0.04/kWh solar |
| Federal ITC | Capex | REON's FEOC position | Ask Tim |
| REON BMS overhead | Capex | Break-even line | +4–6% of system cost (Tim) |

**Open decisions:** reference product (OES vs EBS, because of the possible 50 kW floor) · utility territory (Eversource base) · ConnectedSolutions + CPS stacking (assume none) · ITC on or off.

---

## Sources

| # | Source | Type | Link |
|---|---|---|---|
| S1 | National Grid, ConnectedSolutions C&I Program Materials (MA) | Official | https://www.nationalgridus.com/media/pdfs/bus-ways-to-save/connectedsolutions-programmaterials.pdf |
| S2 | NuWatt, ConnectedSolutions business battery rates MA 2026 | Installer | https://nuwattenergy.com/en/massachusetts/connected-solutions-business-battery-rates-ma-2026 |
| S3 | EnergyBot, Mass Save C&I ConnectedSolutions | Aggregator | https://www.energybot.com/incentives/massachusetts/masssave-electric-ci-connected-solutions-program-22744.html |
| S4 | Rhode Island Energy, ConnectedSolutions battery program guide 2024–26 | Official (RI) | https://bankfive.com/getmedia/477726a8-e30d-4b79-a3f8-08317cbfebb8/RIE_Program-Guide_Battery-Energy-Storage-5-10-2024.pdf |
| S5 | RI EEC, ConnectedSolutions 2027–2029 planning (June 2026) | Official (RI) | https://eec.ri.gov/wp-content/uploads/2026/06/RI-EEC-Meeting_ConnectedSolutions-2027-2029-Planning_06-2026.pdf |
| S6 | National Grid MA, ConnectedSolutions business page | Official | https://www.nationalgridus.com/MA-Business/Energy-Saving-Programs/ConnectedSolutions |
| S7 | Mass.gov, Clean Peak Energy Standard program review | Official | https://www.mass.gov/info-details/clean-peak-energy-standard-program-review |
| S8 | Modo Energy, Massachusetts Clean Peak Energy Certificate for BESS (Jul 2026) | Analyst | https://modoenergy.com/research/isone-ma-clean-peak-cpec-bess-battery-storage |
| S9 | Mass.gov, CPS program details (May 28, 2026 emergency rule) | Official | https://www.mass.gov/info-details/clean-peak-energy-standard-program-details |
| S10 | Mass.gov, CPS emergency rulemaking public hearing (Jul 6, 2026) | Official | https://www.mass.gov/event/public-hearing-clean-peak-energy-standard-emergency-rulemaking-07-06-2026 |
| S11 | Mass.gov, CPS regulation summary presentation | Official | https://www.mass.gov/doc/drafts-cps-reg-summary-presentation/download |
| S12 | Mass.gov, SMART 3.0 (2026 adder table) | Official | https://www.mass.gov/smart30 |
| S13 | Mass.gov, SMART 3.0 overview | Official | https://www.mass.gov/doc/smart-30-overview/download |
| S14 | Eversource, 2024 Summary of Eastern MA Electric Rates (Greater Boston) | Official | https://www.eversource.com/Content/docs/default-source/rates-tariffs/ema-greater-boston-rates.pdf?sfvrsn=10 |
| S15 | NuWatt, commercial storage calculator (cites Eversource Jul 2026 and National Grid 2026 summaries) | Installer | https://nuwattenergy.com/en/commercial-solar/storage/calculator |
| S16 | Nectar, National Grid MA rate guide | Aggregator | https://nectarclimate.com/rates/massachusetts-electric-national-grid |
| S17 | OpenEI Utility Rate Database (example: National Grid G-2 SEMA) | Official data | https://apps.openei.org/IURDB/rate/view/67d08dea7568c8189f03c54e |
| S18 | Competitive Energy Services, ISO-NE capacity auction reforms update | Analyst | https://www.competitive-energy.com/blog/iso-new-england-capacity-auction-reforms-progress-update |
| S19 | Utility Dive, ISO-NE capacity prices (FCA 18) | Trade press | https://utilitydive.com/news/new-england-iso-ne-capacity-prices-rise/708322 |
| S20 | Environment+Energy Leader, ISO-NE 2026 CELT adds BTM battery forecast | Trade press | https://environmentenergyleader.com/stories/iso-ne-2026-celt-report-adds-first-battery-storage-forecast,125780 |
| S21 | Foley Hoag, Massachusetts Section 83E procurement | Law firm | https://foleyhoag.com/news-and-insights/blogs/energy-and-climate-counsel/2025/september/massachusetts-energy-storage-procurement-underway/ |
| S22 | mGrid, Section 83E Round II RFP (Aug 2026) | Trade press | https://mgrid.org/2026/08/08/massachusetts-83e-round-2-rfp-1000mw-storage-distribution-connected-carve-out/ |
| S23 | Energy-Storage.news, Massachusetts issues RFP for 1,000 MW | Trade press | https://www.energy-storage.news/massachusetts-issues-rfp-seeking-1000mw-of-bess/ |
| S24 | Cleanview, Massachusetts battery storage projects | Aggregator | https://cleanview.co/battery-storage-projects/massachusetts |
| S25 | Pulse (summary), Massachusetts distributed solar potential | Secondary | https://www.pulse.bot/energy/news/massachusetts-distributed-solar-potential-reaches-92-gw-as-electrification-demand-rises-9e5a407b-d1db-456e-8e78-2c02aa0bad65/ |
| S26 | Pulse (summary of Solar Power World), battery storage barriers fall in MA | Secondary | https://www.pulse.bot/climatetech/news/battery-storage-moves-forward-in-massachusetts-as-barriers-fall-b4fdff9a-1bea-49e2-8a37-17c9f288a442 |
| S27 | Energy-Storage.news, storage ITC after OBBBA | Trade press | https://www.energy-storage.news/us-energy-storage-to-retain-momentum-post-reconciliation-bill-near-term-rush-to-complete-projects/ |
| S28 | JD Supra, IRS guidance on material assistance (FEOC) | Law firm | https://www.jdsupra.com/legalnews/new-irs-guidance-clarifies-material-5011776/ |
| S29 | Husch Blackwell, FEOC restrictions update | Law firm | https://www.huschblackwell.com/newsandinsights/feoc-restrictions-on-energy-tax-credits-an-update |
| S30 | IRS Notice 2026-15 | Official | https://www.irs.gov/pub/irs-drop/n-26-15.pdf |
| S31 | NREL ATB 2024, commercial battery storage | Official | https://atb.nrel.gov/electricity/2024/commercial_battery_storage |
| S32 | NREL ATB 2025, commercial battery storage | Official | https://atb.nlr.gov/electricity/2025/commercial_battery_storage |
| S33 | Energy-Storage.news, Lazard 2025 LCOS | Trade press citing Lazard | https://www.energy-storage.news/lazard-says-us-energy-storage-cost-reduction-in-2025/ |
| S34 | NREL ComStock public datasets | Official | https://comstock.nrel.gov/page/datasets |
| S35 | ComStock data documentation | Official | https://nrel.github.io/ComStock.github.io/docs/data.html |
| S36 | AWS Open Data, End-Use Load Profiles for the U.S. Building Stock | Official | https://registry.opendata.aws/nrel-pds-building-stock/ |
| S37 | NREL PVWatts | Official tool | https://pvwatts.nrel.gov |
| S38 | Zhou et al. 2026 public data and code | Research | https://github.com/Rico-dicp/Ev-battery-cell-to-cell-inconsistency |
| S39 | Business Wire, Lightshift six new MA projects (Jun 2026) | Press release | https://www.businesswire.com/news/home/20260622969127/en/Lightshift-Energy-Deploys-Six-New-Battery-Storage-Projects-in-Massachusetts |
| S40 | iGrow News, Kearsarge Energy storage | Trade press | https://igrownews.com/kearsarge-energy-latest-news/ |
| S41 | Mass.gov, CPS written comments (BlueWave and others) | Official docket | https://www.mass.gov/doc/cps-written-comments/download |
| S42 | Energy-Storage.news, Trina completes MA projects for Lightshift | Trade press | https://www.energy-storage.news/trina-completes-utility-scale-bess-projects-massachusetts |
| — | REON CTO Tim Ren, hack Discord (Nov 6–7, 2026) | Sponsor | Hack Discord, not public |
