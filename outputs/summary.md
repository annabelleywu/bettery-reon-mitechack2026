# REON fault-intensity model and value demo

All inputs are placeholder assumptions (see `reon_model/simulate.py`).

## 1. Learned fault intensity  lambda_i(t) = lambda_0 exp(beta . x_i(t))

Training rows: 960,132 cell-months, 154 faults.

```
events = 154, exposure = 80004.2, homogeneous MLE = 0.00192
term                          coef          se  rate ratio
log lambda_0               -6.4735      0.0905            
temp_offset_C               0.0821      0.0423       1.086
soh_gap                     6.3028      4.7500     546.072
resistance_gap              3.1133      1.9484      22.495
```
True: log lambda_0 = -6.5023, temp_offset_C = 0.12, soh_gap = 10.0, resistance_gap = 1.5

Likelihood-ratio test vs simple Poisson (all lambdas equal): LR = 273.3, df = 3, p = 6.00e-59

Held-out mean Poisson deviance (lower is better, packs not seen in training):

| model | deviance |
|---|---|
| simple Poisson (one lambda) | 0.00326 |
| NHPP GLM | 0.00290 |
| NHPP gradient boosting | 0.00304 |

### Reduction check: fleet with equal lambdas

True rate 0.004; simple-Poisson MLE sum(y)/sum(e) = 0.00382; GLM slopes = [-0.03, 1.097, 0.881] (SE [0.025, 3.157, 1.302]); LRT p = 0.280 -> no evidence against the simple Poisson process.

## 2. Fixed string vs. per-cell bypass (96s, 59.5 kWh, bypass headroom k = 4, 500 Monte Carlo packs)

| metric | fixed P10 / P50 / P90 | bypass P10 / P50 / P90 |
|---|---|---|
| Retirement year (retention < 70%) | 8.1 / 10.1 / 11.8 | 10.3 / 12.0 / 13.4 |
| Lifetime delivered energy (MWh) | 155.1 / 193.3 / 224.6 | 197.8 / 229.4 / 255.5 |
| Service visits (outages) over 15 y | 5.0 / 8.0 / 12.0 | 1.0 / 1.0 / 2.0 |
| Hard cell faults over 15 y | 5.0 / 8.0 / 12.0 | 5.0 / 8.0 / 12.0 |
| Availability (%) | 96.9 / 98.0 / 98.7 | 99.5 / 99.7 / 99.7 |

Paired difference (same initial cells): +1.75 years of service (P10 0.33, P90 4.00), +32.5 MWh delivered (P10 6.6, P90 74.9).

## 3. Early warning from the learned model (one pack at year 8)

Riskiest cells' predicted fault rates (per year): [0.0492, 0.0041, 0.0036, 0.0035, 0.0034] vs. pack median 0.0015.

P(no outage in next 12 months): fixed 0.816, bypass k=1 0.983, bypass k=2 0.999, bypass k=4 1.000

Figures: `retention_and_retirement.png`, `outage_risk_year8.png`.
