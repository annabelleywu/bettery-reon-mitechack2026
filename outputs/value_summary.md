# Value of cell-level control: Massachusetts C&I site

2 x REON EBS (60 kW / 120 kWh nominal; 250 cells per string, 10% backups), Eversource Greater Boston G-2, from 2027. Team default: 2000 packs per design; other cases: 600; fault cases: 1000. Identical cells in both designs. Inputs and sources: `docs/Methodology_v2.md`, `docs/Reliability_and_Customers_Research.md`, `reon_model/economics.py`.

Energy and life: means over packs. **Money is compared over a 20-year service horizon**: when a block retires the owner buys a new one at that year's price (NREL 2025 mid-case decline) and ITC rate (full through 2033, 75% in 2034, 50% in 2035, none after), pays fixed O&M of 4% of installed cost a year (NLR ATB 2025), and is credited straight-line salvage for the block in service at year 20. NPV gains are means of each pack's paired difference, with P10 and P90.

## Team default, per site, over 20 years

| | Fixed string | Cell-level control |
|---|---|---|
| Blocks bought per position over 20 y | 3.07 | 3.00 |
| Installed cost, present value (after ITC) | $92,979 | $93,511 |
| Revenue, present value (ConnectedSolutions + demand charges + Clean Peak) | $186,856 | $189,708 |
| Fixed O&M, present value | $28,276 | $28,276 |
| Salvage at year 20, present value | $3,373 | $5,543 |
| **20-year NPV** | **$58,848** | **$63,185** |
| Simple payback (median) | 3.1 y | 3.2 y |
| Energy delivered over 20 y (AC) | 752 MWh | 764 MWh |
| Service life per block (mean) | 7.30 y | 8.07 y |
| Year 1: ConnectedSolutions / demand charges / Clean Peak / losses | $7,416 / $11,329 / $2,013 / -$1,107 | $7,460 / $11,398 / $2,025 / -$1,114 |
| Firm kW for 2 h at year 5 (per block) | 26.2 | 27.1 |

Lifetime energy gain per block **+12.1%**, service life gain **+10.6%**. **20-year NPV gain: $4,336 per site** (P10 $1,958, P90 $6,656); over each design's own first life (no replacement) it is $6,566. Extra energy over 20 y: 11.7 MWh. CO2 avoided over 20 y: 3.2 t (operation) + 2.5 t (cells not manufactured). Cells kept out of waste: 221 kg (32 kWh). beta_power at start of life (fixed): 0.880 (paper fleet 0.871).

**Scale-up, per 100 MW of C&I storage** (1,667 two-block sites; Massachusetts had about 220 MW enrolled in ConnectedSolutions in 2025): +$7.2M NPV, +19.4 GWh delivered and 9.5 kt CO2 avoided over 20 years, 368 t of cells not manufactured.

## Customers (same battery, different site)

| Customer | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | 20-y NPV gain per site (P10, P90) | Own-life NPV gain |
|---|---|---|---|---|---|
| Neighborhood grocer: Eversource G-1 demand option ($41.65/kW), 2 blocks | +12.3% | +10.8% | 7.29 / 8.07 | +4.7k (+2.3k, +7.2k) | +7.9k |
| Mid-size business: Eversource G-2 ($33.95/kW), 2 blocks (default) | +12.1% | +10.6% | 7.30 / 8.07 | +4.3k (+2.0k, +6.7k) | +6.6k |
| Cold-storage warehouse: Eversource G-3 ($30.05/kW), 10 blocks | +12.3% | +10.8% | 7.29 / 8.07 | +20.7k (+9.0k, +32.7k) | +30.4k |
| Mid-size business on National Grid G-2 ($15.06/kW), 2 blocks | +12.3% | +10.8% | 7.29 / 8.07 | +3.5k (+1.2k, +5.8k) | +3.8k |

## Cell grades: REON with looser-binned cells vs a fixed string with matched cells

| Case | Lifetime energy | Life | 20-y NPV difference per site (same cell price) |
|---|---|---|---|
| REON with cells 1.5x as uneven vs fixed string with the paper's cells | +6.3% | +5.7% | +0.6k |
| REON with cells 2.0x as uneven vs fixed string with the paper's cells | +0.8% | +1.1% | -3.5k |
| REON with cells 2.5x as uneven vs fixed string with the paper's cells | -4.3% | -3.1% | -7.7k |

Same cell price assumed. Cells are roughly 10-12% of installed cost (BNEF 2025: stationary-storage packs $70/kWh, average cells $74/kWh, against $600/kWh installed), so covering REON's 4% BMS overhead with cheaper cells alone needs a cell discount of roughly a third; any discount is added value.

## All cases (no hard faults)

| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | 20-y NPV gain per site (P10, P90) | Own-life NPV gain |
|---|---|---|---|---|---|
| **Team default**: bypass on empty and on fault, 250 cells, k = 25 (10% backups), no hard faults | +12.1% | +10.6% | 7.30 / 8.07 | +4.3k (+2.0k, +6.7k) | +6.6k |
| k = 0 of 250 | -0.8% | -0.4% | 7.29 / 7.26 | -4.6k (-5.0k, -4.3k) | -2.5k |
| k = 5 of 250 | +5.9% | +5.3% | 7.29 / 7.68 | +0.4k (-1.9k, +2.4k) | +2.0k |
| k = 12 of 250 | +9.0% | +8.0% | 7.29 / 7.87 | +2.4k (+0.0k, +4.7k) | +4.3k |
| k = 50 of 250 | +16.0% | +14.0% | 7.29 / 8.30 | +6.4k (+4.0k, +8.8k) | +9.3k |
| k = 125 of 250 | +21.9% | +19.0% | 7.29 / 8.67 | +9.5k (+6.5k, +12.2k) | +13.4k |
| k = 249 of 250 | +26.3% | +22.8% | 7.29 / 8.95 | +11.6k (+8.6k, +14.6k) | +16.4k |
| Previous setup: 96 cells, k = 4 | +6.2% | +5.6% | 7.45 / 7.86 | +0.4k (-2.1k, +2.6k) | +2.3k |
| Spread 0.5x | +6.0% | +5.5% | 8.04 / 8.49 | -0.1k (-2.6k, +1.7k) | +2.5k |
| Spread 2.0x | +25.0% | +21.2% | 6.08 / 7.37 | +15.7k (+11.5k, +19.9k) | +13.4k |
| Spread 3.0x | +41.2% | +35.6% | 4.99 / 6.76 | +30.9k (+24.6k, +37.2k) | +19.3k |
| Early-knee outliers 5% (knee x0.8) | +19.0% | +17.5% | 6.77 / 7.96 | +8.1k (+5.1k, +11.5k) | +10.6k |
| Add resting (2 lowest remaining-life cells, before knee) | +12.2% | +11.4% | 7.29 / 8.12 | +3.4k (+1.1k, +5.7k) | +6.5k |
| Cycle-dominated aging | +10.9% | +9.9% | 5.19 / 5.70 | +7.0k (+4.9k, +9.2k) | +4.6k |
| Cycle-dominated aging + resting | +11.8% | +11.5% | 5.19 / 5.79 | +7.2k (+5.0k, +9.4k) | +5.0k |
| Slower calendar aging (knee about 10 y, closer to REON's 10-y / 20,000-cycle cells) | +11.8% | +10.4% | 11.44 / 12.63 | +4.2k (+2.6k, +5.9k) | +7.7k |
| Retire at 80% | +11.6% | +9.8% | 6.55 / 7.19 | +5.6k (+3.2k, +8.0k) | +5.9k |
| Retention vs own beginning of life (R_sys) | +12.2% | +10.7% | 7.36 / 8.14 | +4.3k (+1.8k, +6.6k) | +6.8k |
| Switch loss 1.6% (0.5 mOhm at 100 A) | +10.3% | +9.8% | 7.29 / 8.00 | +2.2k (-0.3k, +4.6k) | +5.0k |
| Switch loss 3.2% (1 mOhm at 100 A) | +7.4% | +8.4% | 7.29 / 7.90 | -1.0k (-3.5k, +1.3k) | +2.6k |
| BMS overhead 6% | +12.3% | +10.8% | 7.29 / 8.07 | +2.6k (+0.3k, +5.1k) | +5.7k |
| Demand-charge capture 75% (instead of 50%) | +12.3% | +10.8% | 7.29 / 8.07 | +5.1k (+2.7k, +7.7k) | +9.3k |
| Installed cost $800/kWh | +12.3% | +10.8% | 7.29 / 8.07 | +4.9k (+1.8k, +8.0k) | +6.0k |
| No ITC (cells fail FEOC test) | +12.3% | +10.8% | 7.29 / 8.07 | +5.9k (+3.9k, +8.2k) | +5.8k |
| Horizon 15 years | +12.3% | +10.8% | 7.29 / 8.07 | +3.5k (+1.3k, +5.8k) | +6.7k |

## Hard cell faults (1000 packs; same failure rate for every cell; REON switches a failed cell out and needs a visit only when more than 25 cells are out)

| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | Blocks lost to a fault (fixed / cell-level) | Service visits per site over life (fixed / cell-level) | Blocks bought per position over 20 y (fixed / cell-level) | 20-y NPV gain per site (P10, P90) |
|---|---|---|---|---|---|---|---|
| 10 ppm, base system: repair (14-day outage, $1,500 visit) | +12.2% | +10.6% | 7.27 / 8.05 | 0% / 0% | 0.1 / 0.0 | 3.06 / 3.00 | +4.5k (+2.2k, +6.9k) |
| 10 ppm, base system: retire the block | +12.9% | +11.4% | 7.23 / 8.05 | 1% / 0% | 0.0 / 0.0 | 3.09 / 3.00 | +5.0k (+2.2k, +7.2k) |
| 100 ppm, base system: repair (14-day outage, $1,500 visit) | +12.1% | +10.5% | 7.28 / 8.04 | 0% / 0% | 1.0 / 0.0 | 3.06 / 3.00 | +5.1k (+2.5k, +8.0k) |
| 100 ppm, base system: retire the block | +20.6% | +19.3% | 6.74 / 8.04 | 16% / 0% | 0.0 / 0.0 | 3.37 / 3.00 | +10.7k (+2.6k, +26.8k) |
| 1000 ppm, base system: repair (14-day outage, $1,500 visit) | +11.7% | +9.3% | 7.30 / 7.98 | 0% / 0% | 9.9 / 0.0 | 3.06 / 3.00 | +12.5k (+7.1k, +18.1k) |
| 1000 ppm, base system: retire the block | +126.5% | +130.6% | 3.46 / 7.98 | 83% / 0% | 0.0 / 0.0 | 6.57 / 3.00 | +86.6k (+28.2k, +150.9k) |

Chance that a fault stops a 250-cell block (arithmetic, no aging):

| Per-cell failure rate | Fixed string, 1 y | Fixed string, 10 y | Cell-level (25 backups), 1 y | Cell-level (25 backups), 10 y |
|---|---|---|---|---|
| 10 ppm per cell-year | 0.2% | 2.5% | about 0 | about 0 |
| 100 ppm per cell-year | 2.5% | 22.1% | about 0 | about 0 |
| 1000 ppm per cell-year | 22.1% | 91.8% | about 0 | about 0 |

Run time 1261 s.
