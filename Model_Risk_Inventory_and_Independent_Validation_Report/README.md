# Model Risk Inventory and Independent Validation Report (SR 11-7 style)

**Status:** Built (Python/Excel).

## What it is
A model risk governance package in the SR 11-7 style: a tiered model inventory, a
findings/remediation tracker with severity ratings, and an annual validation plan -
inventorying the actual models built across this portfolio (not hypothetical ones) as if
they were a bank's model population.

## Data
No external data - this is a governance/process deliverable over 5 real models already
built in this portfolio: the Historical Simulation VaR engine, the GARCH(1,1) VaR
challenger (both from this category), the PD/LGD/EAD Expected Loss engine
(`Credit_Risk_PD_LGD_EAD_Modeling`), the Vasicek/CIR short-rate model, and the interest
rate swap valuation model (both from the Quant Finance Bootcamp).

## Method
- **Tiering:** each model rated Tier 1/2/3 by materiality x complexity x usage.
- **Inventory fields:** model ID, name, type, owner, tier, last validated, next validation
  due, key limitations - the standard SR 11-7 inventory schema.
- **Findings tracker:** real limitations discovered while building/backtesting each model
  (e.g. the HS 99% VaR independence failure found in Project 1) logged as findings with
  severity, remediation plan, target date, and status.
- **Annual validation plan:** schedules next validation per model's tier cadence, with one
  model (the PD/LGD/EAD engine) flagged for early revalidation given a genuine vintage-risk
  finding.

## Key findings logged
1. **F-001 (Medium):** HS 95% VaR fails the Christoffersen independence test - directly
   pulled from Project 1's real backtest result, not a hypothetical finding.
2. **F-002 (High):** PD/LGD/EAD model trained on 2007-2014 LendingClub vintage; underwriting
   standards and macro conditions have shifted materially since - a genuine vintage-risk
   limitation of that model, not invented for this exercise.
3. **F-003 (Low):** Single-factor short-rate model cannot capture curve twists - usage
   restriction, not a defect, documented so the model isn't misapplied to curve-sensitive
   products.

## Skills demonstrated
Model risk tiering methodology, SR 11-7 style inventory and findings-tracker construction,
translating a real backtest result (from Project 1) into a governance finding with a
severity rating and remediation plan, and building an annual validation calendar - the
process/governance half of model risk management, distinct from the quantitative modeling
itself.

## Files
- `build_inventory.py` - generates the workbook end to end (`py -3 build_inventory.py`)
- `Model_Risk_Inventory.xlsx` - 3 sheets: Model Inventory, Findings Tracker, Annual
  Validation Plan
