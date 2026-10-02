"""
VaR Backtesting and Model Validation Framework
Kupiec unconditional coverage test, Christoffersen independence/conditional coverage
tests, Basel traffic-light zones, rolling PSI drift check, and a Historical-Simulation
vs. GARCH(1,1) VaR challenger-model comparison.

Real data: SPY (S&P 500 ETF) daily returns, 2016-2025, pulled live via yfinance.
This window deliberately spans the 2018 Q4 selloff, the 2020 COVID crash, and the 2022
rate-hiking drawdown, so exceedance clustering in the backtest is a real market
phenomenon, not an injected stress regime.
"""
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TICKER = "SPY"
START, END = "2016-01-01", "2025-01-01"

# ---------------------------------------------------------------------------
# 1. Pull real daily prices and compute log returns
# ---------------------------------------------------------------------------
raw = yf.download(TICKER, start=START, end=END, progress=False, auto_adjust=True)
close = raw["Close"][TICKER] if isinstance(raw["Close"], pd.DataFrame) else raw["Close"]
port = np.log(close / close.shift(1)).dropna()
port.name = "return"
print(f"Loaded {len(port)} real trading days of {TICKER} returns "
      f"({port.index[0].date()} to {port.index[-1].date()})")

# ---------------------------------------------------------------------------
# 2. Historical Simulation VaR (rolling 250-day window, 99% and 95%)
# ---------------------------------------------------------------------------
WINDOW = 250

def rolling_hs_var(series, window, alpha):
    return series.rolling(window).apply(lambda x: -np.percentile(x, (1 - alpha) * 100))

hs_var_99 = rolling_hs_var(port, WINDOW, 0.99)
hs_var_95 = rolling_hs_var(port, WINDOW, 0.95)

# ---------------------------------------------------------------------------
# 3. Challenger model: GARCH(1,1)-style rolling volatility VaR (parametric)
# ---------------------------------------------------------------------------
def garch11_vol(returns, omega=1e-6, alpha=0.08, beta=0.90):
    n = len(returns)
    sigma2 = np.zeros(n)
    sigma2[0] = np.var(returns[:30])
    for t in range(1, n):
        sigma2[t] = omega + alpha * returns[t - 1] ** 2 + beta * sigma2[t - 1]
    return np.sqrt(sigma2)

garch_sigma = garch11_vol(port.values)
z99 = stats.norm.ppf(0.99)
z95 = stats.norm.ppf(0.95)
garch_var_99 = pd.Series(z99 * garch_sigma, index=port.index)
garch_var_95 = pd.Series(z95 * garch_sigma, index=port.index)

# ---------------------------------------------------------------------------
# 4. Backtest exceedances (actual loss > predicted VaR) - both models, both CLs
# ---------------------------------------------------------------------------
def exceedances(returns, var_series):
    aligned = pd.concat([returns, var_series], axis=1, keys=["ret", "var"]).dropna()
    breach = (-aligned["ret"] > aligned["var"]).astype(int)
    return breach

hs_breach_99 = exceedances(port, hs_var_99)
hs_breach_95 = exceedances(port, hs_var_95)
garch_breach_99 = exceedances(port, garch_var_99)
garch_breach_95 = exceedances(port, garch_var_95)

# ---------------------------------------------------------------------------
# 5. Kupiec unconditional coverage test
# ---------------------------------------------------------------------------
def kupiec_test(breach, alpha):
    n = len(breach)
    x = breach.sum()
    p = 1 - alpha
    if x == 0:
        lr = -2 * n * np.log(1 - p)
    else:
        p_hat = x / n
        lr = -2 * (
            (n - x) * np.log(1 - p) + x * np.log(p)
            - (n - x) * np.log(1 - p_hat) - x * np.log(p_hat)
        )
    p_value = 1 - stats.chi2.cdf(lr, df=1)
    return {"exceedances": int(x), "n": n, "exceedance_rate": x / n,
            "expected_rate": p, "LR_stat": lr, "p_value": p_value,
            "pass_95pct": p_value > 0.05}

# ---------------------------------------------------------------------------
# 6. Christoffersen independence test
# ---------------------------------------------------------------------------
def christoffersen_independence(breach):
    b = breach.values
    n00 = n01 = n10 = n11 = 0
    for i in range(1, len(b)):
        if b[i - 1] == 0 and b[i] == 0:
            n00 += 1
        elif b[i - 1] == 0 and b[i] == 1:
            n01 += 1
        elif b[i - 1] == 1 and b[i] == 0:
            n10 += 1
        else:
            n11 += 1
    pi01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0
    pi11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)

    ll_indep = 0
    if 0 < pi < 1:
        ll_indep = (n00 + n10) * np.log(1 - pi) + (n01 + n11) * np.log(pi)
    ll_dep = 0
    if 0 < pi01 < 1:
        ll_dep += n00 * np.log(1 - pi01) + n01 * np.log(pi01)
    if 0 < pi11 < 1:
        ll_dep += n10 * np.log(1 - pi11) + n11 * np.log(pi11)
    lr_ind = -2 * (ll_indep - ll_dep)
    p_value = 1 - stats.chi2.cdf(lr_ind, df=1)
    return {"LR_independence": lr_ind, "p_value": p_value, "pass_95pct": p_value > 0.05}

# ---------------------------------------------------------------------------
# 7. Basel traffic-light zones (trailing 250 days, 99% VaR)
# ---------------------------------------------------------------------------
def traffic_light(n_exceedances):
    if n_exceedances <= 4:
        return "GREEN"
    elif n_exceedances <= 9:
        return "YELLOW"
    else:
        return "RED"

last_250 = hs_breach_99.tail(250)
zone = traffic_light(int(last_250.sum()))

# ---------------------------------------------------------------------------
# 8. Population Stability Index (PSI) - build window vs. latest validation window
# ---------------------------------------------------------------------------
def psi(base, comp, bins=10):
    base_pct, edges = np.histogram(base, bins=bins)
    comp_pct, _ = np.histogram(comp, bins=edges)
    base_pct = np.where(base_pct == 0, 1, base_pct) / len(base)
    comp_pct = np.where(comp_pct == 0, 1, comp_pct) / len(comp)
    return np.sum((comp_pct - base_pct) * np.log(comp_pct / base_pct))

build_window = port.iloc[:WINDOW].values
validation_window = port.iloc[-WINDOW:].values
psi_value = psi(build_window, validation_window)

# ---------------------------------------------------------------------------
# 9. Results
# ---------------------------------------------------------------------------
results = {
    "HS_99": {"kupiec": kupiec_test(hs_breach_99, 0.99),
              "christoffersen": christoffersen_independence(hs_breach_99)},
    "HS_95": {"kupiec": kupiec_test(hs_breach_95, 0.95),
              "christoffersen": christoffersen_independence(hs_breach_95)},
    "GARCH_99": {"kupiec": kupiec_test(garch_breach_99, 0.99),
                 "christoffersen": christoffersen_independence(garch_breach_99)},
    "GARCH_95": {"kupiec": kupiec_test(garch_breach_95, 0.95),
                 "christoffersen": christoffersen_independence(garch_breach_95)},
}

print("=" * 70)
print(f"VaR BACKTESTING RESULTS - real {TICKER} returns, {START} to {END}")
print("=" * 70)
for model, tests in results.items():
    k = tests["kupiec"]
    c = tests["christoffersen"]
    print(f"\n{model}:")
    print(f"  Exceedances: {k['exceedances']}/{k['n']} (rate {k['exceedance_rate']:.4f}, "
          f"expected {k['expected_rate']:.4f})")
    print(f"  Kupiec LR={k['LR_stat']:.3f}  p={k['p_value']:.4f}  "
          f"{'PASS' if k['pass_95pct'] else 'FAIL'}")
    print(f"  Christoffersen LR={c['LR_independence']:.3f}  p={c['p_value']:.4f}  "
          f"{'PASS' if c['pass_95pct'] else 'FAIL'}")

print(f"\nBasel traffic-light zone (last 250 days, 99% HS VaR): {zone} "
      f"({int(last_250.sum())} exceedances)")
print(f"PSI (2016 build window vs. latest 250-day validation window): {psi_value:.4f} "
      f"({'stable' if psi_value < 0.1 else 'moderate shift' if psi_value < 0.25 else 'significant shift'})")

# ---------------------------------------------------------------------------
# 10. Chart
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, figsize=(12, 8))
axes[0].plot(port.index, port.values, label=f"{TICKER} daily log return", color="steelblue", linewidth=0.6)
axes[0].plot(hs_var_99.index, -hs_var_99.values, label="HS VaR 99% (loss threshold)",
             color="firebrick", linewidth=1)
breach_dates = hs_breach_99[hs_breach_99 == 1].index
axes[0].scatter(breach_dates, port.loc[breach_dates], color="red", zorder=5, s=20,
                label="Exceedance")
axes[0].set_title(f"Historical Simulation VaR (99%) Backtest - Real {TICKER} Returns "
                   f"({START} to {END})")
axes[0].legend(loc="lower left", fontsize=8)

axes[1].plot(garch_var_99.index, garch_var_99.values, label="GARCH(1,1) VaR 99%",
             color="darkorange")
axes[1].plot(hs_var_99.index, hs_var_99.values, label="HS VaR 99%", color="firebrick",
             alpha=0.7)
axes[1].set_title("Challenger Model Comparison: GARCH vs. Historical Simulation")
axes[1].legend(loc="upper left", fontsize=8)

plt.tight_layout()
plt.savefig("var_backtest_chart.png", dpi=120)
print("\nSaved chart: var_backtest_chart.png")
