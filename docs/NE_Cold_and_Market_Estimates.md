# NE Cold site estimate, market size and switch-loss check

Back-of-envelope estimates that sit beside the cell-level model. They use public benchmarks, not site bills, and every step is shown so it can be replaced when real data arrives. Model numbers come from `outputs/value_summary.md` and `scripts/run_value.py` (2,000 paired packs); the rerun cases in section 4 use the same script with the stated inputs changed.

## 1. New England Cold Storage (NE Cold), site estimate

Public facts: 6 Picker Road, Sturbridge, MA; 120,549 sq ft per the Town of Sturbridge special permit (necold.com lists 120,662 sq ft); about 95,000 sq ft frozen; about 25,000 pallet positions; six ALTA EXPERT refrigeration systems; National Grid territory. Sources are listed in `Methodology_v2.md` (N1 to N7). We make no claim about on-site solar or thermal storage; the results below do not include solar.

| Step | Conservative | Mid | Source / reasoning |
|---|---|---|---|
| Floor area | 120,549 sq ft | 120,549 sq ft | Town of Sturbridge permit |
| Electricity intensity | 28.9 kWh/sq ft/yr | 46 kWh/sq ft/yr | MidAmerican Energy refrigerated-warehouse benchmark (low); ASHRAE Journal Feb 2018, large cold storage at 157 kBtu/ft²·yr (mid). ACEEE (2002) reports 40 to 60, so the conservative case sits below the published range |
| Annual use | 3.5 GWh | 5.5 GWh | 120,549 × 28.9 = 3.48 GWh; × 46 = 5.55 GWh |
| Average load | ~400 kW | ~630 kW | annual use ÷ 8,760 h (398 kW; 633 kW). Peak is unknown and at least the average, so this errs low |
| Battery size | 10 to 20% of average load = 40 to 80 kW, so 2 blocks | 63 to 126 kW, so 2 to 4 blocks | one EBS block is 30 kW / 60 kWh |
| Rate class | National Grid G-3 (likely) | same | G-3 applies above 200 kW average demand. The G-3 demand charge was not found; **to confirm from NE Cold's bill** |
| REON gain over conventional | +$3.5k (low +$1.2k, high +$5.8k) at 2 blocks | about +$7.0k at 4 blocks | model's National Grid G-2 case ($15.06/kW); per-block value is similar across cases (4 × $1.75k) |

Open inputs: NE Cold's bills or 15-minute interval data, its rate class and the G-3 demand charge.

### Model rerun for the NE Cold case (National Grid G-2 at $15.06/kW, 2 blocks, 2,000 packs, no solar)

| | Conventional | REON |
|---|---|---|
| 20-year NPV per site, today's dollars | $1.2k | $4.7k |
| Simple payback (median) | 5.1 y | 5.2 y |
| Year-1 net value | about $13.3k | about $13.4k |

REON's gain over conventional: mean +$3.5k (P10 +$1.2k, P90 +$5.8k), +12.1% lifetime energy, +10.6% service life. At $15.06/kW the battery alone is only thinly positive (payback past 5 years), so for NE Cold the argument rests on reliability and on scale, not on a large absolute return. The model's 30% ITC is assumed; without it the Eversource G-2 gain is +$5.9k (“All cases” table in `outputs/value_summary.md`).

Why the dashboard shows $3,364 and the Python model +$3.5k: the browser model runs 48 paired packs, the Python model 2,000. Both are inside the cross-check tolerance (`webapp/checks/crosscheck.js`).

### Demand window versus a 2-hour battery

National Grid G-3 measures peak demand from 8 a.m. to 9 p.m. on weekdays. A 2-hour battery cannot hold a steady load down for 13 hours. The model assumes the monthly peak lasts about 2 hours and captures **50%** of the theoretical demand-charge saving (75% is tested: +$5.1k instead of +$4.3k on the default site). Interval data from the site will show the real peak shape.

## 2. Market size (Massachusetts and United States)

| Step | Massachusetts | United States | Source / reasoning |
|---|---|---|---|
| Refrigerated space | 12 warehouses; 54.4M gross cu ft | 931 warehouses; 3.99B gross cu ft | USDA NASS, Capacity of Refrigerated Warehouses 2025 Summary (Feb 2026) |
| Volume to floor area | ÷ 47 ft = 1.16M sq ft | ÷ 47 ft = 84.9M sq ft | RLS Complete, Sturbridge: 3.9M cu ft over 83,000 sq ft. A taller divisor gives less floor area (conservative) |
| Annual electricity | 33 GWh | 2.45 TWh | × 28.9 kWh/sq ft (low benchmark) |
| Average load | 3.8 MW | 280 MW | ÷ 8,760 h |
| Battery potential (10 to 20%) | 0.4 to 0.8 MW; 13 to 25 blocks | 28 to 56 MW; 930 to 1,870 blocks | same sizing rule as section 1; 30 kW per block |
| Installed value | $0.5 to 0.9M | $34 to 67M | about $36k per block ($600/kWh × 60 kWh) |
| REON gain over conventional | about $23 to 52k | about $1.6 to 3.9M | $1.75k per block (National Grid G-2 case) to $2.07k per block (Eversource G-3 case, $20.7k ÷ 10) |
| CO₂ avoided (20 y), solar-charged | about 37 to 71 t | about 2.7 to 5.3 kt | 2.85 t per block (1.60 t operation + 1.25 t cells) |
| CO₂ avoided (20 y), grid-charged | about 16 to 31 t | about 1.2 to 2.3 kt | 1.25 t per block (cells not manufactured only) |

Why this is conservative: low-end energy benchmark, battery sized to average rather than peak load, and only USDA-surveyed warehouses (food-processor cold rooms and distribution centers are excluded). The main uncertainty is the 10 to 20% sizing share, which a site dispatch study would replace.

## 3. Operating CO₂ assumes solar charging

The per-site CO₂ figure (5.7 t over 20 years = 3.2 t operation + 2.5 t cells not manufactured) and the per-100 MW figure (9.5 kt) assume the battery charges from on-site solar. For a grid-charged site the operating credit is zero and only the cells-not-manufactured part remains (about 44% of the total). The dollar results do not depend on solar. In the Python model this is `solar_charge_share` (default 1.0); in the dashboard, the Engineering view setting "Share of battery charging from on-site solar".

## 4. Switch-loss check at the block's rated current

The original switch-resistance cases were run at 100 A. A 30 kW block of 250 cells at about 3.1 V per cell carries about 38.7 A at full power (30,000 W ÷ (250 × 3.1 V)). Switch loss scales as current × resistance ÷ cell voltage, so:

| Case | Loss | Lifetime energy | Service life | 20-y NPV gain per site (P10, P90) |
|---|---|---|---|---|
| Base case (model default) | 0.5% | +12.1% | +10.6% | +$4.3k (+$2.0k, +$6.7k) |
| 0.5 mΩ at 100 A | 1.6% | +10.3% | +9.8% | +$2.2k (−$0.3k, +$4.6k) |
| **1 mΩ at the rated 38.7 A** | **1.25%** | **+10.8%** | **+9.9%** | **+$2.9k (+$0.5k, +$5.2k)** |
| 1 mΩ at 100 A | 3.2% | +7.4% | +8.4% | −$1.0k (−$3.5k, +$1.3k) |

At the rated current a 1 mΩ switch keeps the gain positive. Interpolating the 1.25% and 3.2% cases puts the break-even near 2.7% loss. The actual per-cell switch resistance is still unknown (REON's CTO describes the overhead as "very minimum overhead, but not none"), so this stays on the open-items list.
