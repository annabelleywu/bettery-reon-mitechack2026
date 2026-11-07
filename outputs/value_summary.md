# Value of cell-level control: Massachusetts C&I site

2 x REON EBS (60 kW / 120 kWh nominal), Eversource Greater Boston G-2, from 2027. 300 packs per design, identical cells in both designs, sudden faults off. Inputs and sources: `docs/Methodology_v2.md`, `reon_model/economics.py`.

## Team default, per site (medians)

| | Fixed string | Cell-level control |
|---|---|---|
| Installed cost after ITC | $49,997 | $51,997 |
| Year 1: ConnectedSolutions | $7,374 | $7,286 |
| Year 1: demand charges | $16,900 | $16,698 |
| Year 1: Clean Peak | $2,002 | $1,978 |
| Year 1: battery losses | -$1,101 | -$1,088 |
| Year 1 net | $25,175 | $24,874 |
| Simple payback | 2.01 y | 2.13 y |
| NPV over service life | $76,366 | $79,645 |
| Energy delivered (AC) | 274 MWh | 291 MWh |
| Service life | 7.42 y | 7.96 y |
| Firm kW for 2 h at year 5 (per block) | 26.2 | 26.0 |

NPV gain from cell-level control: **$3,172** per site (P10 $289, P90 $7,083). Extra energy 17.0 MWh. CO2 avoided: 4.6 t (operation) + 1.7 t (cells not manufactured over 20 y). Cells kept out of waste: 153 kg (22 kWh). beta_power at start of life (fixed): 0.893 (paper fleet 0.871).

## All cases

| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | NPV gain per site (P10, P90) |
|---|---|---|---|---|
| **Team default**: bypass on empty + rest before knee, k = 4 | +5.9% | +7.3% | 7.42 / 7.96 | +3.2k (+0.3k, +7.1k) |
| Bypass on empty only, k = 4 | +5.6% | +4.5% | 7.42 / 7.75 | +3.4k (+0.4k, +7.3k) |
| Bypass only, k = 0 | -0.5% | -1.1% | 7.42 / 7.33 | -2.7k (-3.4k, -2.6k) |
| Bypass only, k = 2 | +3.9% | +3.4% | 7.42 / 7.67 | +1.0k (-1.3k, +5.2k) |
| Bypass only, k = 8 | +8.7% | +7.3% | 7.42 / 7.96 | +6.2k (+2.9k, +10.1k) |
| Bypass only, k = 16 | +12.1% | +10.1% | 7.42 / 8.17 | +9.3k (+6.3k, +13.0k) |
| Bypass only, k = 32 | +15.8% | +13.5% | 7.42 / 8.42 | +13.0k (+9.5k, +17.1k) |
| Bypass only, k = 95 | +22.6% | +19.1% | 7.42 / 8.83 | +19.3k (+16.0k, +23.4k) |
| Spread 0.5x | +2.7% | +5.2% | 8.00 / 8.42 | -0.3k (-2.0k, +1.7k) |
| Spread 1.5x | +8.1% | +9.1% | 6.83 / 7.46 | +5.3k (+1.4k, +10.9k) |
| Spread 2.0x | +11.4% | +12.0% | 6.25 / 7.00 | +7.0k (+2.5k, +14.3k) |
| Spread 3.0x | +19.7% | +18.8% | 5.33 / 6.33 | +11.9k (+5.3k, +20.7k) |
| Early-knee outliers 5% (knee x0.8) | +10.0% | +12.0% | 6.92 / 7.75 | +6.2k (+1.2k, +11.3k) |
| Rest threshold 0% | +5.9% | +7.3% | 7.42 / 7.96 | +3.2k (+0.3k, +7.1k) |
| Rest threshold 30% | +5.9% | +7.3% | 7.42 / 7.96 | +3.2k (+0.3k, +7.1k) |
| Rest threshold 50% | +5.9% | +7.3% | 7.42 / 7.96 | +3.1k (+0.3k, +7.1k) |
| Rest all life (no stop) | +4.8% | +5.6% | 7.42 / 7.83 | +2.0k (-0.9k, +5.9k) |
| Cycle-dominated aging, bypass only | +4.8% | +4.8% | 5.25 / 5.50 | +2.0k (-0.4k, +5.0k) |
| Cycle-dominated aging, rest before knee | +8.8% | +11.1% | 5.25 / 5.83 | +4.9k (+2.3k, +8.2k) |
| Retire at 80% | +4.1% | +5.7% | 6.58 / 6.96 | +1.0k (-1.6k, +4.9k) |
| Retention vs own beginning of life (R_sys) | +5.9% | +7.3% | 7.46 / 8.00 | +3.2k (+0.2k, +7.1k) |
| BMS overhead 6% | +5.9% | +7.3% | 7.42 / 7.96 | +2.2k (-0.7k, +6.1k) |
| National Grid G-2 ($15.06/kW-month) | +5.9% | +7.3% | 7.42 / 7.96 | +1.2k (-0.7k, +3.6k) |
| Sudden faults on (placeholder rates) | +4.0% | +5.1% | 7.42 / 7.79 | +1.5k (-2.2k, +5.8k) |

Run time 119 s.
