"""Experiment constants — the only file with hardcoded values."""

from datetime import date

EXPERIMENT_NAME = "Don't Show, Tell"
EXPERIMENT_START = date(2026, 2, 10)

SHEET_ID = "1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ"
SHEET_TAB = "Form Responses 1"

# The 7 columns actually used (out of 37 in the sheet)
COL_TIMESTAMP = "Timestamp"
COL_VISIT_TYPE = "Visit Type"
COL_OPENER_OUTCOME = "Opener Outcome"
COL_QUESTIONS_ASKED = "Questions Asked"
COL_GOLDEN_FLOW = "Golden Flow Amount"
COL_QR_SETUP = "QR Setup Done"
COL_AMBASSADOR = "Ambassador Name"

SKIP_QUESTIONS = {"no", "none", "n/a", "-", ""}
QR_YES_VALUES = {"yes", "true", "done", "1"}
FUNNEL_STEPS = ["Visits", "Opener Passed", "Demos", "Onboardings"]
MIN_VISITS_FOR_INSIGHT = 5
MAX_DROPOFF_QUESTIONS = 5

AMBASSADOR_NAMES = {
    "Arslan Ansari": "Arslan Ansari",
    "Afsar Khan": "Afsar Khan",
    "Sharoon Sam93": "Sharoon Javed",
    "Zahid Khan": "Muhammad Zahid",
    "Junaid Ahmed": "Junaid Ahmed",
    "irfan rana": "Muhammad Irfan",
    "Umer Daniyal": "Umer Daniyal",
    "Owais Feroz": "Owais Feroz",
}
