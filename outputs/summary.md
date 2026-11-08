> **v1 demo output** (`scripts/run_demo.py`): 96-cell block, 4 backups, placeholder fault hazard. It documents the learned fault-intensity model. Current results: [`value_summary.md`](value_summary.md).

# REON fault-intensity model and value demo

Cell-aging spread is calibrated on Zhou et al. (2026) per-cell data (`outputs/calibration_report.md`). The stationary timeline, pack design and every fault-hazard number are placeholder assumptions (`reon_model/simulate.py`).

## 1. Learned fault intensity  lambda_i(t) = lambda_0 exp(beta . x_i(t))

Training rows: 960,064 cell-months, 153 faults. The model sees the MEASURED signals (`MonitoringConfig()`: all brief signals, placeholder noise); the true hazard is driven by the true temperature, SOH gap and resistance gap.

```
events = 153, exposure = 79999.4, homogeneous MLE = 0.00191
term                          coef          se  rate ratio
log lambda_0               -6.6502      0.1043            
temp_offset_C               0.1552      0.0404       1.168
soh_gap                    11.6067      4.7371  109835.757
resistance_gap              0.9024      1.0342       2.465
eod_voltage_gap            -2.4287     13.1394       0.088
ocv_gap                     2.8250     13.7935      16.860
soc_end                    -0.1873      0.8913       0.829
fade_rate_gap               3.2330      2.9296      25.356
```
True hazard: log lambda_0 = -6.5023, temp_offset_C = 0.12, soh_gap = 10.0, resistance_gap = 1.5

Likelihood-ratio test vs simple Poisson (all lambdas equal): LR = 156.9, df = 7, p = 1.44e-30

Held-out mean Poisson deviance (lower is better, packs not seen in training):

| model | deviance |
|---|---|
| simple Poisson (one lambda) | 0.00316 |
| NHPP GLM | 0.00304 |
| NHPP gradient boosting | 0.00307 |

### Reduction check: fleet with equal lambdas

True rate 0.004; simple-Poisson MLE sum(y)/sum(e) = 0.00437; GLM slopes = [-0.001, 2.535, -0.192, 1.166, -1.655, 0.66, -1.969] (SE [0.023, 3.012, 0.666, 8.421, 8.682, 0.315, 1.734]); LRT p = 0.637 -> no evidence against the simple Poisson process.

### Which monitored signals matter (held-out deviance, lower is better)

Each row reruns the same 120-pack fleet (identical cells and faults) with a different `MonitoringConfig`.

| monitoring | features | deviance |
|---|---|---|
| none (simple Poisson) | 0 | 0.00316 |
| all brief signals, placeholder noise (default) | 7 | 0.00304 |
| all brief signals, no noise | 7 | 0.00304 |
| conventional BMS view: voltage + temperature | 2 | 0.00306 |
| no capacity / SOH / history | 5 | 0.00304 |
| capacity + resistance + temperature only | 3 | 0.00304 |

## 2. Fixed string vs. per-cell bypass (96s, 59.5 kWh, bypass headroom k = 4, 500 Monte Carlo packs)

| metric | fixed P10 / P50 / P90 | bypass P10 / P50 / P90 |
|---|---|---|
| Retirement year (retention < 70%) | 6.5 / 7.4 / 8.5 | 6.8 / 7.6 / 8.8 |
| Lifetime delivered energy (MWh) | 125.8 / 143.6 / 163.7 | 130.6 / 147.7 / 170.3 |
| Service visits (outages) over 15 y | 2.0 / 5.0 / 8.0 | 0.0 / 0.0 / 1.0 |
| Hard cell faults over 15 y | 2.0 / 5.0 / 8.0 | 2.0 / 4.0 / 8.0 |
| Availability (%) | 98.0 / 98.7 / 99.5 | 99.7 / 100.0 / 100.0 |

Paired difference (same initial cells): +0.17 years of service (P10 -0.08, P90 0.50), +4.9 MWh delivered (P10 -0.7, P90 11.0).

## 2b. Capacity value vs. bypass headroom (faults off, 300 packs, median)

k = cells the voltage window lets drop out; k = 95 is every cell running to its own end (a conceptual upper bound that ignores the voltage window).

| scenario | fixed: life (y) / MWh | k=2 | k=4 | k=8 | k=16 | k=32 | k=95 |
|---|---|---|---|---|---|---|---|
| knee at fade-matched 6.6 y (default) | 7.4 / 143 | +3% life, +4% MWh | +4% life, +6% MWh | +7% life, +9% MWh | +10% life, +12% MWh | +13% life, +16% MWh | +19% life, +23% MWh |
| knee at 10 y | 10.5 / 200 | +4% life, +4% MWh | +4% life, +6% MWh | +7% life, +8% MWh | +10% life, +12% MWh | +12% life, +16% MWh | +18% life, +22% MWh |
| knee at 14 y | 14.2 / 263 | +4% life, +4% MWh | +5% life, +6% MWh | +7% life, +9% MWh | +9% life, +12% MWh | +11% life, +16% MWh | +16% life, +22% MWh |
| as-fitted post-knee spread | 7.2 / 139 | +3% life, +4% MWh | +5% life, +6% MWh | +8% life, +9% MWh | +12% life, +13% MWh | +15% life, +17% MWh | +23% life, +26% MWh |

## 2c. When to bypass: control policies (k = 4, placeholder faults, 300 packs, median)

Every decision uses measured signals only. Isolating takes a cell out for good; resting takes it out for one month. Both use bypass slots, keeping one spare for faults.

| policy | life (y) | MWh | service visits | availability | cells isolated |
|---|---|---|---|---|---|
| fixed string (baseline) | 7.42 | 142.5 | 7 | 98.55% | 0.0 |
| bypass on empty + on fault (default) | 7.58 | 147.4 | 1 | 99.83% | 0.0 |
| bypass on fault only | 7.33 | 140.4 | 1 | 99.82% | 0.0 |
| + isolate cells > 8% below pack SOH | 7.50 | 144.6 | 3 | 99.28% | 13.1 |
| + isolate cells with learned risk > 0.02 / y | 7.50 | 146.2 | 2 | 99.39% | 10.8 |
| + rest the 2 weakest cells each month | 7.75 | 146.9 | 1 | 99.87% | 0.0 |

## 3. Early warning from the learned model (one pack at year 8)

Riskiest cells' predicted fault rates (per year): [0.0312, 0.018, 0.0095, 0.0094, 0.008] vs. pack median 0.0014.

P(no outage in next 12 months): fixed 0.800, bypass k=1 0.979, bypass k=2 0.999, bypass k=4 1.000

Figures: `retention_and_retirement.png`, `value_vs_headroom.png`, `outage_risk_year8.png`.
