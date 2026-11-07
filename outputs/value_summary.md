# Value of cell-level control: Massachusetts C&I site

2 x REON EBS (60 kW / 120 kWh nominal; 250 cells per string, 10% backups), Eversource Greater Boston G-2, from 2027. Team default: 2000 packs per design; other cases: 600. Identical cells in both designs. Inputs and sources: `docs/Methodology_v2.md`, `docs/Reliability_and_Customers_Research.md`, `reon_model/economics.py`.

Energy and life: means over packs. Dollars: medians over packs; NPV gain is the median of each pack's paired difference.

## Team default, per site

| | Fixed string | Cell-level control |
|---|---|---|
| Installed cost after ITC | $50,400 | $52,416 |
| Year 1: ConnectedSolutions | $7,416 | $7,460 |
| Year 1: demand charges | $16,994 | $17,096 |
| Year 1: Clean Peak | $2,013 | $2,025 |
| Year 1: battery losses | -$1,107 | -$1,114 |
| Year 1 net | $25,315 | $25,468 |
| Simple payback | 2.02 y | 2.08 y |
| NPV over service life | $74,696 | $84,234 |
| Energy delivered (AC) | 270 MWh | 303 MWh |
| Service life (mean) | 7.30 y | 8.07 y |
| Firm kW for 2 h at year 5 (per block) | 26.2 | 27.1 |

Lifetime energy gain **+12.1%**, service life gain **+10.6%** (per pack: P10 +0.50 y, P90 +1.08 y). NPV gain from cell-level control: **$9,071** per site (P10 $6,351, P90 $12,826). Extra energy 32.0 MWh. CO2 avoided: 8.7 t (operation) + 2.5 t (cells not manufactured over 20 y). Cells kept out of waste: 221 kg (32 kWh). beta_power at start of life (fixed): 0.880 (paper fleet 0.871).

## All cases (no hard faults)

| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | NPV gain per site (P10, P90) |
|---|---|---|---|---|
| **Team default**: bypass on empty and on fault, 250 cells, k = 25 (10% backups), no hard faults | +12.1% | +10.6% | 7.30 / 8.07 | +9.1k (+6.4k, +12.8k) |
| k = 0 of 250 | -0.8% | -0.4% | 7.29 / 7.26 | -2.7k (-3.5k, -2.6k) |
| k = 5 of 250 | +5.9% | +5.3% | 7.29 / 7.68 | +3.2k (+0.7k, +7.3k) |
| k = 12 of 250 | +9.0% | +8.0% | 7.29 / 7.87 | +6.2k (+3.4k, +10.1k) |
| k = 50 of 250 | +16.0% | +14.0% | 7.29 / 8.30 | +12.7k (+9.8k, +16.5k) |
| k = 125 of 250 | +21.9% | +19.0% | 7.29 / 8.67 | +17.9k (+15.0k, +22.0k) |
| k = 249 of 250 | +26.3% | +22.8% | 7.29 / 8.95 | +21.9k (+19.0k, +25.9k) |
| Previous setup: 96 cells, k = 4 | +6.2% | +5.6% | 7.45 / 7.86 | +3.5k (+0.5k, +7.6k) |
| Spread 0.5x | +6.0% | +5.5% | 8.04 / 8.49 | +3.8k (+2.2k, +6.2k) |
| Spread 2.0x | +25.0% | +21.2% | 6.08 / 7.37 | +17.9k (+13.4k, +24.7k) |
| Spread 3.0x | +41.2% | +35.6% | 4.99 / 6.76 | +25.5k (+19.2k, +35.8k) |
| Early-knee outliers 5% (knee x0.8) | +19.0% | +17.5% | 6.77 / 7.96 | +14.5k (+9.6k, +20.0k) |
| Add resting (2 lowest remaining-life cells, before knee) | +12.2% | +11.4% | 7.29 / 8.12 | +9.0k (+6.0k, +12.6k) |
| Cycle-dominated aging | +10.9% | +9.9% | 5.19 / 5.70 | +6.4k (+4.0k, +9.6k) |
| Cycle-dominated aging + resting | +11.8% | +11.5% | 5.19 / 5.79 | +7.0k (+4.6k, +10.4k) |
| Retire at 80% | +11.6% | +9.8% | 6.55 / 7.19 | +8.3k (+5.5k, +12.0k) |
| Retention vs own beginning of life (R_sys) | +12.2% | +10.7% | 7.36 / 8.14 | +9.4k (+6.4k, +13.1k) |
| Switch loss 1.6% (0.5 mOhm at 100 A) | +10.3% | +9.8% | 7.29 / 8.00 | +7.1k (+4.3k, +11.0k) |
| BMS overhead 6% | +12.3% | +10.8% | 7.29 / 8.07 | +8.3k (+5.4k, +12.2k) |
| National Grid G-2 ($15.06/kW-month) | +12.3% | +10.8% | 7.29 / 8.07 | +5.0k (+3.1k, +7.3k) |
| No ITC (cells fail FEOC test) | +12.3% | +10.8% | 7.29 / 8.07 | +8.4k (+5.5k, +12.3k) |

## Hard cell faults (1000 packs; same failure rate for every cell; REON switches a failed cell out and needs a visit only when more than 25 cells are out)

| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | Blocks lost to a fault (fixed / cell-level) | Service visits per site over life (fixed / cell-level) | NPV gain per site (P10, P90) |
|---|---|---|---|---|---|---|
| 10 ppm, base system: repair (14-day outage, $1,500 visit) | +12.2% | +10.6% | 7.27 / 8.05 | 0% / 0% | 0.1 / 0.0 | +9.1k (+6.2k, +13.4k) |
| 10 ppm, base system: retire the block | +12.9% | +11.4% | 7.23 / 8.05 | 1% / 0% | 0.0 / 0.0 | +9.1k (+6.2k, +13.7k) |
| 100 ppm, base system: repair (14-day outage, $1,500 visit) | +12.1% | +10.5% | 7.28 / 8.04 | 0% / 0% | 1.0 / 0.0 | +9.4k (+6.4k, +13.7k) |
| 100 ppm, base system: retire the block | +20.6% | +19.3% | 6.74 / 8.04 | 16% / 0% | 0.0 / 0.0 | +9.7k (+6.4k, +36.9k) |
| 1000 ppm, base system: repair (14-day outage, $1,500 visit) | +11.7% | +9.3% | 7.30 / 7.98 | 0% / 0% | 9.9 / 0.0 | +12.9k (+8.4k, +18.5k) |
| 1000 ppm, base system: retire the block | +126.5% | +130.6% | 3.46 / 7.98 | 83% / 0% | 0.0 / 0.0 | +71.1k (+9.1k, +121.1k) |

Chance that a fault stops a 250-cell block (arithmetic, no aging):

| Per-cell failure rate | Fixed string, 1 y | Fixed string, 10 y | Cell-level (25 backups), 1 y | Cell-level (25 backups), 10 y |
|---|---|---|---|---|
| 10 ppm per cell-year | 0.2% | 2.5% | about 0 | about 0 |
| 100 ppm per cell-year | 2.5% | 22.1% | about 0 | about 0 |
| 1000 ppm per cell-year | 22.1% | 91.8% | about 0 | about 0 |

Run time 908 s.
