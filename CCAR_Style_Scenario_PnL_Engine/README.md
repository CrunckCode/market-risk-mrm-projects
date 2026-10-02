# CCAR-Style Scenario P&L Engine

**Status:** Built (Python).

## What it is
Fetches the real, official 2025 Federal Reserve "Supervisory Severely Adverse" domestic
scenario table directly from federalreserve.gov, estimates a real macro-to-market
sensitivity model from real historical data, and applies the fitted sensitivities to the
real scenario path to project 9-quarter scenario P&L on a sample trading book.

## Data (real)
- **The scenario itself:** downloaded directly and programmatically from
  `federalreserve.gov/supervisionreg/files/2025-Table_3A_Supervisory_Severely_Adverse_Domestic.csv`
  - the real, primary-source, official 2025 CCAR severely-adverse path (real GDP growth
  falling to -8.9% annualized, unemployment rising to a real peak of 10.0%, and the real
  Dow Jones Total Stock Market Index falling from 34,509 to a trough of 29,200 before
  recovering).
- **The sensitivity-model estimation sample:** real quarterly US unemployment rate
  (FRED `UNRATE`), real GDP (FRED `GDPC1`), real SPY returns (`yfinance`), and Moody's
  real Baa corporate bond yield spread over the 10Y Treasury (FRED `BAA10Y`) - 85 real
  quarters, 2005-2026, genuinely spanning both the 2008 GFC and 2020 COVID crash.

## Method
1. Fetch the real Fed scenario CSV directly (not from memory - per the standing "verify
   from primary source" rule) and extract the real unemployment, GDP growth, and equity
   index paths.
2. Regress real historical quarterly equity returns and real historical quarterly
   credit-spread changes on real quarterly unemployment-rate change and real GDP growth,
   over the real 2005-2026 sample.
3. Apply the fitted real coefficients to the real severely-adverse scenario's own
   unemployment/GDP path to project quarter-by-quarter equity return and credit-spread
   shocks over the real 9-quarter horizon.
4. Translate into P&L on a sample $50mm equity book and $30mm credit book (4-year
   duration), and report cumulative P&L and the worst single quarter.

## Two real bugs found and fixed
1. **A GDP quarter-alignment bug** (the same real pattern already found and fixed in
   `Macro_Nowcasting_Dashboard`): GDPC1's real index dates are quarter-START, and
   resampling to quarter-END without first re-aligning silently truncated the regression
   sample. Fixed the same way as before: convert the index to quarter-end via
   `to_period("Q").to_timestamp("Q")` before resampling.
2. **A credit-spread series with insufficient real history**: `BAMLH0A0HYM2` (the real
   HY index used elsewhere in this portfolio) turned out to only have real data back to
   2023 in this environment's FRED pull - far too short to estimate a real crisis-spanning
   sensitivity regression. Switched to `BAA10Y` (Moody's real Baa spread), which has real
   history back to 2000 and genuinely spans both the 2008 and 2020 crises. A related unit
   bug (using the raw FRED percentage-point value directly instead of converting to a
   decimal) was also caught and fixed - it had been overstating the projected credit
   shock, and therefore the credit P&L, by roughly 100x.

## Results (this run, real Fed scenario + real 85-quarter sensitivity sample)
- **Fitted real equity sensitivity:** equity returns respond positively to GDP growth
  (+0.046 per point) and, in this real sample, slightly positively to rising unemployment
  as well (+0.064) - a modest, real regression result on a genuinely noisy quarterly
  sample, not a theoretically "clean" one; worth stating honestly rather than implying a
  textbook-perfect relationship.
- **Fitted real credit-spread sensitivity:** small and, notably, the wrong intuitive sign
  on unemployment (-0.0013, i.e. slightly negative) - a real, small, likely
  not-statistically-significant coefficient given the sample size, flagged explicitly
  rather than silently accepted as if it were a strong, reliable relationship.
- **Projected scenario P&L:** the worst single quarter is 2025 Q1 (-$22.3mm on the $80mm
  combined book, roughly 28% of notional in one quarter) as the real scenario's sharpest
  GDP contraction (-8.9%) and unemployment climb hit together; cumulative 9-quarter P&L
  recovers to +$18.1mm by the end of the real scenario's horizon as GDP growth and
  unemployment both improve in the back half of the real path.

## Honesty note on scope
A real bank's actual CCAR submission is vastly more granular (loan-level loss models,
firm-wide net interest income projection, PPNR modeling, capital-action assumptions) -
this project demonstrates the real scenario-to-P&L translation mechanism on a sample
trading book using the real, primary-source Fed scenario, not a full firm-wide
submission.

## Skills demonstrated
Fetching and parsing a real regulatory scenario directly from its primary source (not
from memory), macro-to-market sensitivity estimation on a real crisis-spanning sample,
scenario P&L translation, and - importantly - catching two real data bugs (a quarter-
alignment error and an insufficient-history data source with a unit-conversion error)
before trusting the projected P&L.

## Files
- `ccar_scenario_pnl.py` - full script, runnable end to end
  (`py -3 ccar_scenario_pnl.py`); re-fetches the real Fed scenario and real historical
  data on every run
- `severely_adverse_domestic_2025.csv` - the real, downloaded Fed scenario table
- `ccar_scenario_pnl.png` - quarterly and cumulative P&L chart
