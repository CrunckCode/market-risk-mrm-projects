# Liquidity Risk and Funding Stress Test Model

**Status:** Built (Python).

## What it is
A Basel III Liquidity Coverage Ratio (LCR) calculation on a constructed bank-scale balance
sheet, using the real, BCBS-published LCR haircut and runoff-rate schedule (not invented
percentages), a maturity-bucketed contractual funding gap analysis, and a combined
market-shock-plus-funding-shock survival-horizon stress test.

## Data
The balance sheet itself is constructed (no public API exposes a specific bank's internal
balance sheet), sized and proportioned to resemble a real large regional bank's 10-Q
structure. **The regulatory parameters applied to it are real, not invented:** Basel III
LCR haircuts (Level 1 HQLA 0%, Level 2A 15%, Level 2B 50%), the real outflow-rate schedule
by liability type (stable retail 3%, less-stable retail 10%, operational wholesale 25%,
non-operational unsecured wholesale 40%, financial-institution wholesale funding 100%),
the real Level 2 asset cap (40% of total HQLA) and Level 2B sub-cap (15%), and the real
75% cap on contractual inflows offsetting outflows.

## Method
1. Apply real BCBS haircuts to each asset category to compute HQLA, then apply the real
   Level 2/Level 2B caps (checked whether the cap actually binds - it did not in this run,
   since Level 2 assets were already under 40% of total HQLA before capping).
2. Apply real BCBS runoff rates to each liability category to compute 30-day gross
   outflows; apply the real 75% inflow cap to net them down.
3. Compute LCR = HQLA / Net Cash Outflows and check against the real 100% Basel III
   minimum.
4. Build a maturity-bucketed funding gap table (contractual inflows vs. outflows across
   0-30 days, 1-3 months, 3-12 months, >12 months) and track cumulative gap.
5. Run a survival-horizon test under four scenarios: base case, market shock alone (+15%
   HQLA haircut, simulating a bond-market selloff), funding shock alone (1.75x runoff
   acceleration), and both combined - isolating which shock type actually drives liquidity
   risk for this balance sheet.

## Results (this run)
- **HQLA:** $29,650M (Level 1 $20,000M + Level 2 $9,650M - Level 2 cap did not bind)
- **Net cash outflows (30-day):** $18,900M (gross $22,500M less $3,600M capped inflows)
- **LCR: 156.9%** - passes the 100% minimum with meaningful headroom, and sits above the
  110-135% range typical of real large US bank 10-Q LCR disclosures, meaning this
  constructed balance sheet is deliberately somewhat conservative/liquid rather than
  optimized for capital efficiency.
- **Funding gap:** cumulative gap turns and stays negative from the very first bucket
  (-$12,400M by 0-30 days), widening to -$23,400M beyond 12 months - the bank is
  structurally reliant on rolling funding rather than closing the gap with contractual
  asset maturities, a realistic feature of any bank balance sheet (maturity
  transformation is the business model, not a flaw by itself).
- **Survival horizon:** 48 days base case, dropping to 41 days under a market shock alone,
  27 days under a funding shock alone, and 23 days combined. **The funding shock has a
  materially larger independent impact (21 days lost) than the market shock (7 days
  lost)** - for this balance sheet, an accelerated deposit/wholesale outflow is the more
  dangerous scenario, not a market-value haircut on HQLA, which is a genuinely useful risk
  finding a real liquidity risk team would want to know.

## Honesty note on scope
The balance sheet composition is constructed for realism, not pulled from a specific
bank's real disclosures; the regulatory haircuts, runoff rates, and caps applied to it are
the real Basel III LCR rule. The maturity-gap contractual cash flows are simplified
(assumed profile, not derived from individual instrument cash flows).

## Skills demonstrated
Real Basel III LCR mechanics (HQLA categorization and caps, outflow/inflow runoff-rate
application), maturity-bucketed funding gap construction, and scenario-based
survival-horizon stress testing that decomposes and ranks market vs. funding risk drivers
- the standard liquidity-risk-analyst deliverable.

## Files
- `liquidity_stress_test.py` - full script, runnable end to end
  (`py -3 liquidity_stress_test.py`)
