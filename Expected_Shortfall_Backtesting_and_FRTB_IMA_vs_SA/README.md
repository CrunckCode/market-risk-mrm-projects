# Expected Shortfall Backtesting and FRTB IMA vs. Standardized Approach

**Status:** Built (Python).

## What it is
Computes rolling 97.5% Expected Shortfall two ways (Historical Simulation and a
Cornish-Fisher parametric adjustment for real skew/kurtosis) on real SPY returns,
backtests both via the exceedance-residual test (there is no single accepted ES
backtest as clean as Kupiec for VaR), and compares FRTB Internal Models Approach (IMA)
capital against the Standardized Approach capital methodology from the companion
`FRTB_Standardized_Approach_Capital_Calculator` project.

## Data (real)
Same real SPY daily log returns, 2016-01-05 to 2024-12-31 (2,263 real trading days,
spanning the 2018 selloff, 2020 COVID crash, and 2022 drawdown), already validated in
`VaR_Backtesting_and_Model_Validation_Framework`.

## Method
1. **Historical Simulation ES:** rolling 250-day window, mean of losses beyond the
   97.5th percentile.
2. **Cornish-Fisher ES:** the real, standard Cornish-Fisher quantile expansion (using
   the window's own empirical skew/kurtosis) applied to VaR, then scaled up by the real
   analytic normal ES/VaR ratio to get an ES estimate. This construction is used
   specifically because there is no single standard closed-form Cornish-Fisher ES in the
   literature (CF is a quantile adjustment, not a full tail-density model) - the ratio
   scaling guarantees ES >= VaR by construction, which a real, defensible approximation
   must satisfy.
3. **Exceedance-residual backtest:** on every real VaR breach day, compute
   (realized loss - VaR) / (ES - VaR) and t-test whether the average residual across all
   breach days is statistically indistinguishable from 1.0 (the theoretical value if the
   tail shape is correctly specified).
4. **IMA vs. SA capital:** IMA capital = 60-day average ES x 1.5 (real BCBS "green zone"
   multiplier), reported as a % of notional; SA capital = the real 25% equity risk
   weight from the companion FRTB project, also as a % of notional - both reported
   scale-invariantly so the comparison doesn't depend on matching a specific book size.

## A real, caught-and-fixed formula bug
An initial Cornish-Fisher ES implementation produced an ES estimate BELOW the
Historical Simulation VaR at the same confidence level - impossible by definition, since
ES is defined as the average loss beyond VaR and must always be at least as large.
Fixed by rebuilding the CF-ES calculation to explicitly guarantee ES >= VaR (scaling the
CF-adjusted VaR-from-mean by the real analytic normal ES/VaR ratio, which is always
greater than 1), rather than trusting an ad hoc formula that happened to violate this
basic mathematical constraint.

## Results (this run, real SPY data)
- **Most recent rolling 97.5% ES:** Historical Simulation 2.27%, Cornish-Fisher 2.09%,
  vs. VaR (same window) of 1.69% - the correct ordering (both ES estimates above VaR,
  HS-ES slightly above the CF estimate, consistent with SPY's real return distribution
  having heavier realized tails than a CF-adjusted-normal approximation fully captures).
- **Exceedance-residual backtest:** mean residual 1.168 across 70 real VaR breach days
  (3.48% of the sample), not statistically distinguishable from the theoretical value of
  1.0 (t=1.282, p=0.204) - the HS-ES model's tail-shape assumption is **not rejected** by
  this real backtest.
- **IMA vs. SA: IMA capital (3.13% of notional) is only 0.13x of SA capital (25.00% of
  notional)** - a large, real, well-documented finding: the Basel III output floor
  (capital must be at least 72.5% of the SA number even under an approved IMA model)
  **binds heavily** for this position, meaning the Standardized Approach's flat,
  conservative risk weight - not the statistically-fitted internal model - is what
  actually determines the real capital requirement. This is exactly the real tension
  regulators intended: IMA can be far more capital-efficient based on real historical
  behavior, but the output floor prevents that efficiency from being fully realized.

## Skills demonstrated
Expected Shortfall estimation via two real methodologies, a real ES-specific backtest
(exceedance-residual, since Kupiec/Christoffersen are VaR-specific), the real FRTB
IMA-vs-SA-and-output-floor mechanic, and - importantly - catching and fixing a formula
that violated the basic ES >= VaR mathematical relationship before trusting its output.

## Files
- `es_backtesting_ima_vs_sa.py` - full script, runnable end to end
  (`py -3 es_backtesting_ima_vs_sa.py`); pulls fresh real SPY data on every run
