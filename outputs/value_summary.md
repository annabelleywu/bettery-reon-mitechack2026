# Value of cell-level control: Massachusetts C&I site

2 x REON EBS (60 kW / 120 kWh nominal), Eversource Greater Boston G-2, from 2027. Team default: 3000 packs per design; other cases: 1000. Identical cells in both designs, sudden faults off. Inputs and sources: `docs/Methodology_v2.md`, `reon_model/economics.py`.

Energy and life: means over packs. Dollars: medians over packs; NPV gain is the median of each pack's paired difference.

## Team default, per site

| | Fixed string | Cell-level control |
|---|---|---|
| Installed cost after ITC | $50,400 | $52,416 |
| Year 1: ConnectedSolutions | $7,434 | $7,345 |
| Year 1: demand charges | $17,036 | $16,832 |
| Year 1: Clean Peak | $2,018 | $1,994 |
| Year 1: battery losses | -$1,110 | -$1,097 |
| Year 1 net | $25,378 | $25,074 |
| Simple payback | 2.01 y | 2.13 y |
| NPV over service life | $77,003 | $80,540 |
| Energy delivered (AC) | 277 MWh | 295 MWh |
| Service life (mean) | 7.45 y | 8.05 y |
| Firm kW for 2 h at year 5 (per block) | 26.4 | 26.2 |

Lifetime energy gain **+6.5%**, service life gain **+8.0%** (per pack: P10 +0.33 y, P90 +0.92 y). NPV gain from cell-level control: **$3,000** per site (P10 $311, P90 $7,024). Extra energy 16.8 MWh. CO2 avoided: 4.5 t (operation) + 1.9 t (cells not manufactured over 20 y). Cells kept out of waste: 168 kg (24 kWh). beta_power at start of life (fixed): 0.892 (paper fleet 0.871).

## All cases

| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | NPV gain per site (P10, P90) |
|---|---|---|---|---|
| **Team default**: bypass on empty + rest before knee, k = 4 | +6.5% | +8.0% | 7.45 / 8.05 | +3.0k (+0.3k, +7.0k) |
| Bypass on empty only, k = 4 | +5.9% | +5.4% | 7.44 / 7.84 | +3.3k (+0.5k, +7.3k) |
| Bypass only, k = 0 | -0.8% | -0.3% | 7.44 / 7.41 | -2.7k (-3.5k, -2.6k) |
| Bypass only, k = 2 | +3.7% | +3.5% | 7.44 / 7.70 | +1.1k (-1.3k, +4.9k) |
| Bypass only, k = 8 | +8.7% | +7.7% | 7.44 / 8.01 | +6.0k (+3.1k, +10.0k) |
| Bypass only, k = 16 | +12.0% | +10.6% | 7.44 / 8.22 | +9.3k (+6.0k, +13.3k) |
| Bypass only, k = 32 | +16.0% | +14.0% | 7.44 / 8.48 | +12.9k (+9.7k, +17.2k) |
| Bypass only, k = 95 | +22.9% | +20.0% | 7.44 / 8.93 | +19.2k (+15.9k, +23.3k) |
| Spread 0.5x | +2.5% | +4.4% | 8.12 / 8.48 | -0.5k (-2.1k, +1.6k) |
| Spread 1.5x | +9.2% | +10.2% | 6.85 / 7.55 | +5.1k (+1.5k, +10.5k) |
| Spread 2.0x | +11.8% | +12.1% | 6.33 / 7.10 | +7.0k (+2.2k, +13.5k) |
| Spread 3.0x | +19.5% | +19.1% | 5.36 / 6.38 | +11.3k (+4.8k, +21.0k) |
| Early-knee outliers 5% (knee x0.8) | +9.8% | +11.5% | 7.03 / 7.84 | +5.7k (+1.7k, +11.6k) |
| Rest threshold 0% | +6.4% | +8.0% | 7.44 / 8.03 | +3.0k (+0.3k, +6.9k) |
| Rest threshold 30% | +6.4% | +8.0% | 7.44 / 8.03 | +3.0k (+0.3k, +6.9k) |
| Rest threshold 50% | +6.4% | +8.0% | 7.44 / 8.03 | +3.0k (+0.3k, +6.9k) |
| Rest all life (no stop) | +5.1% | +6.4% | 7.44 / 7.92 | +1.9k (-0.9k, +5.7k) |
| Cycle-dominated aging, bypass only | +5.2% | +4.9% | 5.29 / 5.55 | +1.9k (-0.4k, +5.2k) |
| Cycle-dominated aging, rest before knee | +9.1% | +10.8% | 5.29 / 5.86 | +4.7k (+2.1k, +8.0k) |
| Retire at 80% | +4.1% | +5.3% | 6.67 / 7.03 | +0.9k (-1.8k, +4.7k) |
| Retention vs own beginning of life (R_sys) | +6.5% | +8.1% | 7.50 / 8.11 | +3.1k (+0.3k, +7.0k) |
| BMS overhead 6% | +6.4% | +8.0% | 7.44 / 8.03 | +2.0k (-0.7k, +5.9k) |
| National Grid G-2 ($15.06/kW-month) | +6.4% | +8.0% | 7.44 / 8.03 | +1.1k (-0.6k, +3.5k) |
| Sudden faults on (placeholder rates) | +4.3% | +5.5% | 7.47 / 7.88 | +1.4k (-2.4k, +5.4k) |

Run time 468 s.
