# REON fault-intensity model and value demo

Cell-aging spread is calibrated on Zhou et al. (2026) per-cell data (`outputs/calibration_report.md`). The stationary timeline, pack design and every fault-hazard number are placeholder assumptions (`reon_model/simulate.py`).

## 1. Learned fault intensity  lambda_i(t) = lambda_0 exp(beta . x_i(t))

Training rows: 959,955 cell-months, 164 faults.

```
events = 164, exposure = 79989.6, homogeneous MLE = 0.00205
term                          coef          se  rate ratio
log lambda_0               -6.6379      0.1016            
temp_offset_C               0.1806      0.0402       1.198
soh_gap                    13.1478      1.7766  512902.641
resistance_gap              0.4762      0.7093       1.610
```
True: log lambda_0 = -6.5023, temp_offset_C = 0.12, soh_gap = 10.0, resistance_gap = 1.5

Likelihood-ratio test vs simple Poisson (all lambdas equal): LR = 205.6, df = 3, p = 2.62e-44

Held-out mean Poisson deviance (lower is better, packs not seen in training):

| model | deviance |
|---|---|
| simple Poisson (one lambda) | 0.00325 |
| NHPP GLM | 0.00308 |
| NHPP gradient boosting | 0.00314 |

### Reduction check: fleet with equal lambdas

True rate 0.004; simple-Poisson MLE sum(y)/sum(e) = 0.00437; GLM slopes = [0.014, 0.51, -0.228] (SE [0.023, 1.668, 0.55]); LRT p = 0.927 -> no evidence against the simple Poisson process.

## 2. Fixed string vs. per-cell bypass (96s, 59.5 kWh, bypass headroom k = 4, 500 Monte Carlo packs)

| metric | fixed P10 / P50 / P90 | bypass P10 / P50 / P90 |
|---|---|---|
| Retirement year (retention < 70%) | 6.2 / 7.2 / 8.2 | 6.6 / 7.3 / 8.5 |
| Lifetime delivered energy (MWh) | 121.0 / 138.0 / 157.5 | 127.0 / 143.3 / 164.5 |
| Service visits (outages) over 15 y | 2.0 / 5.0 / 9.0 | 0.0 / 0.0 / 1.0 |
| Hard cell faults over 15 y | 2.0 / 5.0 / 9.0 | 2.0 / 4.0 / 8.0 |
| Availability (%) | 97.7 / 98.7 / 99.5 | 99.7 / 100.0 / 100.0 |

Paired difference (same initial cells): +0.25 years of service (P10 -0.08, P90 0.58), +5.5 MWh delivered (P10 0.4, P90 11.3).

## 2b. Capacity value vs. bypass headroom (faults off, 300 packs, median)

k = cells the voltage window lets drop out; k = 95 is every cell running to its own end (a conceptual upper bound that ignores the voltage window).

| scenario | fixed: life (y) / MWh | k=2 | k=4 | k=8 | k=16 | k=32 | k=95 |
|---|---|---|---|---|---|---|---|
| knee at fade-matched 6.6 y (default) | 7.2 / 138 | +3% life, +4% MWh | +5% life, +6% MWh | +7% life, +9% MWh | +10% life, +12% MWh | +14% life, +16% MWh | +20% life, +23% MWh |
| knee at 10 y | 10.1 / 191 | +3% life, +4% MWh | +5% life, +6% MWh | +7% life, +9% MWh | +10% life, +13% MWh | +13% life, +17% MWh | +19% life, +24% MWh |
| knee at 14 y | 13.3 / 248 | +4% life, +4% MWh | +5% life, +6% MWh | +8% life, +10% MWh | +10% life, +13% MWh | +14% life, +18% MWh | +19% life, +25% MWh |
| as-fitted post-knee spread | 6.9 / 134 | +4% life, +4% MWh | +6% life, +6% MWh | +8% life, +9% MWh | +12% life, +14% MWh | +16% life, +18% MWh | +24% life, +27% MWh |

## 3. Early warning from the learned model (one pack at year 8)

Riskiest cells' predicted fault rates (per year): [0.0278, 0.0235, 0.0129, 0.0095, 0.008] vs. pack median 0.0012.

P(no outage in next 12 months): fixed 0.790, bypass k=1 0.977, bypass k=2 0.998, bypass k=4 1.000

Figures: `retention_and_retirement.png`, `value_vs_headroom.png`, `outage_risk_year8.png`.
