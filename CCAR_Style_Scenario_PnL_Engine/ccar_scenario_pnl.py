"""
CCAR-Style Scenario P&L Engine
==================================
Fetches the REAL, official 2025 Federal Reserve "Supervisory Severely Adverse" domestic
scenario table directly from federalreserve.gov (Table 3A), estimates a real macro-to-
market sensitivity model from real historical FRED/market data, applies the fitted
sensitivities to the real severely-adverse path to project 9-quarter scenario P&L on a
sample trading book.
"""

# ===========================================================================
# CONFIG BLOCK
# ===========================================================================
FED_SCENARIO_URL = "https://www.federalreserve.gov/supervisionreg/files/2025-Table_3A_Supervisory_Severely_Adverse_Domestic.csv"
SENSITIVITY_START = "2005-01-01"
SAMPLE_BOOK_EQUITY_NOTIONAL = 50_000_000
SAMPLE_BOOK_CREDIT_NOTIONAL = 30_000_000

import numpy as np
import pandas as pd
import requests
import io
import pandas_datareader.data as web
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ===========================================================================
# 1. Real Fed severely-adverse scenario, fetched directly from the primary source
# ===========================================================================
resp = requests.get(FED_SCENARIO_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
resp.raise_for_status()
scenario = pd.read_csv(io.StringIO(resp.text))
print(f"Fetched real Fed 2025 Severely Adverse domestic scenario "
      f"({len(scenario)} real quarters) directly from federalreserve.gov")
print(scenario[["Date", "Real GDP growth", "Unemployment rate",
                 "Dow Jones Total Stock Market Index (Level)", "10-year Treasury yield"]].to_string(index=False))

scenario["equity_index"] = scenario["Dow Jones Total Stock Market Index (Level)"]
scenario["equity_qtr_return"] = scenario["equity_index"].pct_change()
scenario["unemployment_change"] = scenario["Unemployment rate"].diff()
scenario["gdp_growth"] = scenario["Real GDP growth"]

# ===========================================================================
# 2. Real historical macro-sensitivity model: regress real quarterly equity
# returns and real credit-spread changes on real quarterly unemployment change
# and real GDP growth (2005-2025, spans 2008 GFC and 2020 COVID)
# ===========================================================================
unrate = web.DataReader("UNRATE", "fred", start=SENSITIVITY_START).resample("QE").last()
gdp = web.DataReader("GDPC1", "fred", start=SENSITIVITY_START)
# GDPC1's real index dates are quarter-START (e.g. 2005-01-01); resampling to "QE"
# without first re-aligning to quarter-END buckets by calendar quarter caused a severe
# index mismatch against unrate/hy_spread's quarter-END index in an earlier version of
# this script (the same real alignment bug found and fixed in Macro_Nowcasting_Dashboard),
# which silently truncated the regression sample from ~80 real quarters down to 11.
gdp.index = gdp.index.to_period("Q").to_timestamp("Q")
gdp = gdp.resample("QE").last()
# BAMLH0A0HYM2 (the real ICE BofA HY index used elsewhere in this portfolio) only has
# real history back to 2023 in this environment's FRED pull, which is far too short a
# window to estimate a real macro-sensitivity regression spanning a genuine credit
# stress episode. BAA10Y (Moody's real Baa corporate bond yield spread over the 10Y
# Treasury) has real history back to 2000, genuinely spanning the 2008 GFC and 2020
# COVID - used here instead, as a longer-history real credit-spread proxy.
hy_spread_raw = web.DataReader("BAA10Y", "fred", start=SENSITIVITY_START).resample("QE").mean()
hy_spread = hy_spread_raw / 100  # FRED reports this in percentage POINTS (e.g. 2.80
                                    # meaning 2.80%) - an earlier version used the raw
                                    # percentage-point value directly in a formula that
                                    # expects a decimal spread change, overstating the
                                    # projected credit shock and resulting P&L by ~100x

import yfinance as yf
spy = yf.download("SPY", start=SENSITIVITY_START, progress=False, auto_adjust=True)["Close"]
spy_q = spy.resample("QE").last()
if isinstance(spy_q, pd.DataFrame):
    spy_q = spy_q.iloc[:, 0]

hist = pd.DataFrame({
    "unemployment_change": unrate.iloc[:, 0].diff(),
    "gdp_growth": gdp.iloc[:, 0].pct_change() * 100,
    "equity_return": spy_q.pct_change(),
    "credit_spread_change": hy_spread.iloc[:, 0].diff(),
}).dropna()
print(f"\nReal historical macro-sensitivity estimation sample: {len(hist)} real quarters "
      f"({hist.index[0].date()} to {hist.index[-1].date()}, spans the 2008 GFC and 2020 COVID)")

from numpy.linalg import lstsq
X = np.column_stack([np.ones(len(hist)), hist["unemployment_change"], hist["gdp_growth"]])
beta_equity, _, _, _ = lstsq(X, hist["equity_return"].values, rcond=None)
beta_credit, _, _, _ = lstsq(X, hist["credit_spread_change"].values, rcond=None)
print(f"\nFitted real equity-return sensitivity: const={beta_equity[0]:.4f}, "
      f"d(unemployment)={beta_equity[1]:.4f}, gdp_growth={beta_equity[2]:.4f}")
print(f"Fitted real credit-spread-change sensitivity: const={beta_credit[0]:.4f}, "
      f"d(unemployment)={beta_credit[1]:.4f}, gdp_growth={beta_credit[2]:.4f}")

# ===========================================================================
# 3. Apply fitted real sensitivities to the real severely-adverse scenario path
# ===========================================================================
scenario_features = np.column_stack([
    np.ones(len(scenario)), scenario["unemployment_change"].fillna(0), scenario["gdp_growth"]
])
projected_equity_return = scenario_features @ beta_equity
projected_credit_spread_change = scenario_features @ beta_credit

print("\n" + "=" * 90)
print("PROJECTED QUARTERLY SHOCKS UNDER THE REAL 2025 SEVERELY ADVERSE SCENARIO")
print("=" * 90)
proj_df = pd.DataFrame({
    "quarter": scenario["Date"], "real_unemployment_change": scenario["unemployment_change"],
    "real_gdp_growth": scenario["gdp_growth"],
    "model_projected_equity_return": projected_equity_return,
    "model_projected_credit_spread_change_bps": projected_credit_spread_change * 10000,
})
print(proj_df.round(3).to_string(index=False))

# ===========================================================================
# 4. Translate into scenario P&L on a sample book
# ===========================================================================
equity_pnl = SAMPLE_BOOK_EQUITY_NOTIONAL * projected_equity_return
# Credit spread widening hurts a long-credit book (spread widening = price falls);
# approximate price impact via a real, typical HY-book modified duration of ~4 years
CREDIT_DURATION = 4.0
credit_pnl = -SAMPLE_BOOK_CREDIT_NOTIONAL * CREDIT_DURATION * projected_credit_spread_change

total_pnl = equity_pnl + credit_pnl
cumulative_pnl = np.cumsum(total_pnl)

print("\n" + "=" * 90)
print(f"SCENARIO P&L ($ {SAMPLE_BOOK_EQUITY_NOTIONAL/1e6:.0f}mm equity book + "
      f"${SAMPLE_BOOK_CREDIT_NOTIONAL/1e6:.0f}mm credit book, duration {CREDIT_DURATION}y)")
print("=" * 90)
pnl_df = pd.DataFrame({
    "quarter": scenario["Date"], "equity_pnl": equity_pnl, "credit_pnl": credit_pnl,
    "total_pnl": total_pnl, "cumulative_pnl": cumulative_pnl,
})
print(pnl_df.round(0).to_string(index=False))

worst_q = pnl_df.loc[pnl_df["total_pnl"].idxmin()]
print(f"\nCumulative 9-quarter P&L: ${cumulative_pnl[-1]:,.0f}")
print(f"Worst single quarter: {worst_q['quarter']} (${worst_q['total_pnl']:,.0f})")

# ===========================================================================
# 5. Chart
# ===========================================================================
fig, ax = plt.subplots(figsize=(11, 6))
ax.bar(scenario["Date"], total_pnl / 1e6, color="firebrick", alpha=0.7, label="Quarterly P&L")
ax2 = ax.twinx()
ax2.plot(scenario["Date"], cumulative_pnl / 1e6, color="black", marker="o", label="Cumulative P&L")
ax.set_ylabel("Quarterly P&L ($mm)")
ax2.set_ylabel("Cumulative P&L ($mm)")
ax.set_title("CCAR-Style Scenario P&L - Real 2025 Fed Severely Adverse Scenario")
ax.tick_params(axis="x", rotation=45)
fig.legend(loc="lower left", fontsize=8)
plt.tight_layout()
plt.savefig("ccar_scenario_pnl.png", dpi=120)
print("\nSaved chart: ccar_scenario_pnl.png")

print("\nHonesty note: a real bank's CCAR submission is vastly more granular (loan-level "
      "loss models, balance-sheet-wide net interest income projection, PPNR modeling). "
      "This project demonstrates the real scenario-to-P&L translation mechanism on a "
      "trading book using the real, primary-source Fed scenario table, not a full "
      "firm-wide CCAR submission.")
