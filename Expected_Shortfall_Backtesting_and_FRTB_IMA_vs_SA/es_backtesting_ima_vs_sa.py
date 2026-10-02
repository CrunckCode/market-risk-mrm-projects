"""
Expected Shortfall Backtesting and FRTB IMA vs. Standardized Approach
==========================================================================
Computes rolling 97.5% Expected Shortfall (ES) two ways - Historical Simulation and a
Cornish-Fisher parametric adjustment for real, empirically-measured skew/kurtosis - on
real SPY returns (the same series validated in VaR_Backtesting_and_Model_Validation_
Framework), backtests both via the exceedance-residual test, then compares FRTB
Internal Models Approach (IMA) capital against the Standardized Approach capital already
computed in FRTB_Standardized_Approach_Capital_Calculator.
"""

# ===========================================================================
# CONFIG BLOCK
# ===========================================================================
TICKER = "SPY"
START, END = "2016-01-01", "2025-01-01"
ES_CONFIDENCE = 0.975
WINDOW = 250
IMA_MULTIPLIER = 1.5   # real BCBS "green zone" backtesting multiplier

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

raw = yf.download(TICKER, start=START, end=END, progress=False, auto_adjust=True)
close = raw["Close"][TICKER] if isinstance(raw["Close"], pd.DataFrame) else raw["Close"]
returns = np.log(close / close.shift(1)).dropna()
print(f"Loaded {len(returns)} real trading days of {TICKER} returns "
      f"({returns.index[0].date()} to {returns.index[-1].date()})")

# ===========================================================================
# 1. Rolling ES via Historical Simulation and Cornish-Fisher
# ===========================================================================
def rolling_hs_es(series, window, confidence):
    def es_calc(x):
        var_cutoff = np.percentile(x, (1 - confidence) * 100)
        tail = x[x <= var_cutoff]
        return -tail.mean() if len(tail) > 0 else np.nan
    return series.rolling(window).apply(es_calc)

def cornish_fisher_es(series, window, confidence):
    """Cornish-Fisher-adjusted VaR (the real, standard quantile expansion using empirical
    skew/kurtosis), extended to ES by applying the real analytic normal ES/VaR ratio to
    the CF-adjusted quantile. There is no single standard closed-form Cornish-Fisher ES
    in the literature (the CF expansion is a quantile adjustment, not a full tail-density
    model), so this construction is an approximation - but it is built to GUARANTEE
    ES >= VaR by construction (multiplying the CF-VaR-from-mean by a ratio that is always
    > 1 for a normal-based ES/VaR relationship), which an earlier ad hoc version of this
    formula violated (it produced ES below VaR, which is impossible by definition since
    ES averages losses beyond VaR)."""
    z = stats.norm.ppf(1 - confidence)          # negative, e.g. ~-1.96 at 97.5%
    phi_z = stats.norm.pdf(z)
    es_var_ratio = (phi_z / (1 - confidence)) / (-z)   # always > 1

    def cf_es(x):
        mu, sigma = x.mean(), x.std()
        skew, kurt = stats.skew(x), stats.kurtosis(x)  # excess kurtosis
        z_cf = (z + (z**2 - 1) * skew / 6 + (z**3 - 3*z) * kurt / 24
                - (2*z**3 - 5*z) * skew**2 / 36)
        var_cf_from_mean = -sigma * z_cf            # positive loss magnitude, from the mean
        es_cf_from_mean = var_cf_from_mean * es_var_ratio
        return es_cf_from_mean - mu
    return series.rolling(window).apply(cf_es)

hs_es = rolling_hs_es(returns, WINDOW, ES_CONFIDENCE)
cf_es = cornish_fisher_es(returns, WINDOW, ES_CONFIDENCE)
var_hs = returns.rolling(WINDOW).apply(lambda x: -np.percentile(x, (1 - ES_CONFIDENCE) * 100))

print(f"\nMost recent rolling 97.5% ES: Historical Sim = {hs_es.iloc[-1]:.4%}, "
      f"Cornish-Fisher = {cf_es.iloc[-1]:.4%}")
print(f"Most recent rolling 97.5% VaR (for comparison): {var_hs.iloc[-1]:.4%}")

# ===========================================================================
# 2. Exceedance-residual backtest: on each VaR breach day, check whether the
# realized-loss-beyond-VaR is consistent with the model's implied tail shape
# ===========================================================================
aligned = pd.concat([returns, var_hs, hs_es], axis=1, keys=["ret", "var", "es"]).dropna()
breach = -aligned["ret"] > aligned["var"]
breach_days = aligned[breach]
print(f"\nVaR breach days: {len(breach_days)} of {len(aligned)} ({len(breach_days)/len(aligned):.2%})")

residuals = (-breach_days["ret"] - breach_days["var"]) / (breach_days["es"] - breach_days["var"])
residuals = residuals.replace([np.inf, -np.inf], np.nan).dropna()
t_stat, p_value = stats.ttest_1samp(residuals, 1.0)
print(f"\nExceedance-residual test: mean residual = {residuals.mean():.3f} (theoretical "
      f"value under correct tail shape = 1.0)")
print(f"t-test vs. 1.0: t={t_stat:.3f}, p={p_value:.4f} - "
      f"{'PASS (tail shape not rejected)' if p_value > 0.05 else 'FAIL (tail shape rejected - model underestimates tail severity)' if residuals.mean() > 1 else 'FAIL (model overestimates tail severity)'}")

# ===========================================================================
# 3. IMA capital (60-day average ES x multiplier) vs. FRTB SA capital
# ===========================================================================
ima_capital_pct = IMA_MULTIPLIER * hs_es.dropna().tail(60).mean()  # as a % of notional
print(f"\nIMA capital (60-day avg ES x {IMA_MULTIPLIER} multiplier), as a % of notional: "
      f"{ima_capital_pct:.2%}")

# Real FRTB SA capital as a % of notional, using the same real equity risk weight
# already applied to the single-name SPY-equivalent equity bucket in the companion
# FRTB_Standardized_Approach_Capital_Calculator project - reported as a %, not a dollar
# amount, so this comparison is scale-invariant and doesn't depend on matching book sizes
RW_EQUITY = 0.25
sa_capital_pct = RW_EQUITY
print(f"FRTB SA capital (equity bucket, {RW_EQUITY:.0%} risk weight), as a % of notional: "
      f"{sa_capital_pct:.2%}")

output_floor_ratio = ima_capital_pct / sa_capital_pct
print(f"\nIMA / SA ratio: {output_floor_ratio:.2f}x")
print(f"Real Basel III output floor requires capital >= 72.5% of the SA number even under "
      f"an approved IMA model - "
      f"{'IMA is ABOVE the floor already (SA does not bind)' if output_floor_ratio >= 0.725 else 'IMA would be floored UP to 72.5% of SA - the SA number binds, not the model'}")
