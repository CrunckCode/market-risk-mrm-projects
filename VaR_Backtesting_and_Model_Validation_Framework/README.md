# VaR Backtesting and Model Validation Framework

**Status:** Built (Python).

## What it is
An independent model-validation layer on top of a VaR model: Kupiec unconditional coverage
test, Christoffersen independence and conditional-coverage tests, Basel traffic-light zone
classification, a rolling Population Stability Index (PSI) check for input-distribution
drift, and a Historical-Simulation-vs-GARCH(1,1) challenger-model comparison.

## Data (real, not simulated)
**SPY (S&P 500 ETF) daily prices, 2016-01-05 to 2024-12-31 (2,263 real trading days),
pulled live via `yfinance`.** This window was chosen deliberately - it spans the 2018 Q4
selloff, the March 2020 COVID crash, and the 2022 rate-hiking drawdown, so any exceedance
clustering found in the backtest is a real market phenomenon, not an injected stress regime.
Log returns computed from adjusted close.

## Method
- **Historical Simulation VaR:** rolling 250-day window, 99% and 95% confidence.
- **GARCH(1,1) VaR (challenger):** rolling conditional volatility (omega=1e-6, alpha=0.08,
  beta=0.90 - fixed, not re-estimated) scaled by the normal quantile at each confidence
  level.
- **Kupiec test:** likelihood-ratio test of whether the observed exceedance rate matches
  the expected rate (1 - confidence level).
- **Christoffersen test:** likelihood-ratio test of whether exceedances are independent
  over time (catches clustering that Kupiec alone misses).
- **Basel traffic light:** classifies the trailing 250 days of 99% VaR exceedances into
  green (<=4), yellow (5-9), red (10+) zones.
- **PSI:** compares the return distribution in the 2016 model-build window to the most
  recent 250-day validation window to flag distributional drift.

## Results (real SPY data, run on 2026-09-26)
| Model | Exceedances | Kupiec | Christoffersen |
|---|---|---|---|
| HS 99% | 32/2014 (1.59% vs. 1.00% expected) | **FAIL (p=0.014)** | **FAIL (p=0.0013)** |
| HS 95% | 103/2014 (5.11% vs. 5.00% expected) | PASS (p=0.81) | **FAIL (p=0.0002)** |
| GARCH 99% | 58/2263 (2.56% vs. 1.00% expected) | **FAIL (p<0.0001)** | PASS (p=0.68) |
| GARCH 95% | 126/2263 (5.57% vs. 5.00% expected) | PASS (p=0.22) | PASS (p=0.14) |

Basel traffic-light zone (99% HS VaR, trailing 250 days): **YELLOW** (6 exceedances).
PSI (2016 build window vs. latest 250-day validation window): **0.071 - stable**.

## Validation finding (the actual "memo" conclusion)
Neither model is unambiguously clean at 99% confidence on real 2016-2024 SPY data. **HS
99% VaR fails both coverage and independence** - it under-predicts tail risk (more real
losses breached it than the model expects) and those breaches cluster in time, almost
certainly concentrated around the March 2020 COVID crash where realized volatility spiked
far faster than a 250-day rolling window could adapt. **GARCH(1,1) 99% VaR fails coverage
in the other direction** - with these fixed, un-refit parameters it produces too many
exceedances overall (2.56% vs. 1.00% expected), though its exceedances are at least
independent (not clustered), suggesting the parameters are miscalibrated for this
instrument rather than the model form being wrong. At 95% confidence, HS passes average
coverage but still fails independence, while GARCH passes both. **Recommended rating:**
99% VaR under both models needs remediation before production use - HS needs a
volatility-scaling overlay or shorter effective lookback to react faster to regime
changes, and GARCH needs re-estimated (not fixed) parameters. The 95% GARCH model is the
only one clean on all four tests in this run.

## Honesty note on scope
This is a single-instrument (SPY) backtest built for a coursework-style demonstration of
methodology, not a production multi-asset VaR validation. A real bank validation would run
this across the full trading book with position-level P&L, not one ETF's price return.

## Skills demonstrated
Kupiec/Christoffersen backtesting methodology, Basel traffic-light approach, GARCH(1,1)
volatility modeling as a VaR challenger, Population Stability Index drift monitoring, and
translating statistical test output (including two models each failing in different ways)
into a defensible model-validation rating - exactly the deliverable a Model Validation /
Model Risk analyst produces, using real market data through a real crisis period.

## Files
- `var_backtesting.py` - full script, runnable end to end (`py -3 var_backtesting.py`);
  pulls fresh SPY data from Yahoo Finance on every run
- `var_backtest_chart.png` - P&L vs. VaR exceedance chart and GARCH-vs-HS comparison chart
