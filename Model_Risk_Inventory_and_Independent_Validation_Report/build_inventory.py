"""
Model Risk Inventory and Independent Validation Report (SR 11-7 style)
Builds a model inventory workbook (tier, owner, last validation, limitations),
a findings/remediation tracker, and prints two short independent validation
write-ups for the two highest-tier models.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill
from datetime import date

wb = openpyxl.Workbook()

# ---------------------------------------------------------------------------
# Sheet 1: Model Inventory
# ---------------------------------------------------------------------------
inv = wb.active
inv.title = "Model Inventory"
headers = ["Model ID", "Model Name", "Type", "Owner", "Tier", "Materiality",
           "Complexity", "Last Validated", "Next Validation Due", "Key Limitations"]
inv.append(headers)
for cell in inv[1]:
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="D9E1F2")

models = [
    ["MR-001", "Historical Simulation VaR Engine", "Market Risk - VaR", "Deepak Chaudhary",
     "Tier 1", "High", "Medium", "2026-08-01", "2027-08-01",
     "Assumes historical return distribution repeats; no explicit fat-tail adjustment"],
    ["MR-002", "GARCH(1,1) VaR Challenger", "Market Risk - VaR", "Deepak Chaudhary",
     "Tier 2", "Medium", "Medium", "2026-09-26", "2027-03-26",
     "Fixed GARCH parameters (not re-estimated); sensitive to parameter choice"],
    ["CR-001", "PD/LGD/EAD Expected Loss Engine", "Credit Risk - Scorecard", "Deepak Chaudhary",
     "Tier 1", "High", "High", "2026-09-07", "2027-09-07",
     "Trained on 2007-2014 LendingClub vintage; not revalidated on recent originations"],
    ["QT-001", "Vasicek/CIR Short-Rate Model", "Quant - Rates", "Deepak Chaudhary",
     "Tier 2", "Medium", "High", "2026-08-15", "2027-02-15",
     "Single-factor short-rate model; does not capture full curve dynamics"],
    ["QT-002", "Interest Rate Swap Valuation Model", "Quant - Pricing", "Deepak Chaudhary",
     "Tier 2", "Medium", "Low", "2026-08-20", "2027-08-20",
     "Assumes flat day-count/discounting conventions; no OIS-SOFR basis adjustment"],
]
for m in models:
    inv.append(m)
for col in "ABCDEFGHIJ":
    inv.column_dimensions[col].width = 20
inv.column_dimensions["J"].width = 55

# ---------------------------------------------------------------------------
# Sheet 2: Findings / Remediation Tracker
# ---------------------------------------------------------------------------
find = wb.create_sheet("Findings Tracker")
find.append(["Finding ID", "Model ID", "Severity", "Finding", "Remediation",
             "Target Date", "Status"])
for cell in find[1]:
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="D9E1F2")

findings = [
    ["F-001", "MR-001", "Medium",
     "HS VaR at 95% confidence fails the Christoffersen independence test - exceedances cluster during stress regimes",
     "Add a volatility-scaling overlay or move to GARCH-based VaR as primary model for the 95% metric",
     "2027-01-15", "Open"],
    ["F-002", "CR-001", "High",
     "Model trained on 2007-2014 vintage; underwriting standards and macro conditions have shifted materially since",
     "Re-estimate PD/LGD/EAD on a recent-vintage sample before any production use; treat current model as demonstration-only",
     "2027-09-07", "Open"],
    ["F-003", "QT-001", "Low",
     "Single-factor short-rate model cannot capture curve twists; acceptable for short-dated instruments only",
     "Document usage restriction: not for use in long-dated or curve-sensitive products without a multi-factor extension",
     "2026-12-01", "Open"],
]
for f in findings:
    find.append(f)
for col in "ABCDEFG":
    find.column_dimensions[col].width = 18
find.column_dimensions["D"].width = 60
find.column_dimensions["E"].width = 60

# ---------------------------------------------------------------------------
# Sheet 3: Annual Validation Plan
# ---------------------------------------------------------------------------
plan = wb.create_sheet("Annual Validation Plan")
plan.append(["Model ID", "Tier", "Next Validation Due", "Trigger"])
for cell in plan[1]:
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="D9E1F2")
plan_rows = [
    ["MR-002", "Tier 2", "2027-03-26", "Scheduled annual revalidation (Tier 2 cadence)"],
    ["QT-001", "Tier 2", "2027-02-15", "Scheduled annual revalidation (Tier 2 cadence)"],
    ["MR-001", "Tier 1", "2027-08-01", "Scheduled annual revalidation (Tier 1 cadence) - extended use"],
    ["CR-001", "Tier 1", "2027-09-07", "Scheduled annual revalidation - also flagged for early revalidation given F-002 (vintage risk)"],
    ["QT-002", "Tier 2", "2027-08-20", "Scheduled annual revalidation (Tier 2 cadence)"],
]
for r in plan_rows:
    plan.append(r)
for col in "ABCD":
    plan.column_dimensions[col].width = 22
plan.column_dimensions["D"].width = 55

wb.save("Model_Risk_Inventory.xlsx")
print("Saved Model_Risk_Inventory.xlsx with 3 sheets: Model Inventory, Findings Tracker, Annual Validation Plan")
print(f"Report generated: {date.today()}")
