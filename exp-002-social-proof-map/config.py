"""Experiment constants — the only file with hardcoded values."""

from datetime import date

EXPERIMENT_NAME = "Social Proof Map"

# Person-based split with staggered start dates.
# Phase 1 (Feb 11-15): Sharoon only.  Phase 2 (Feb 16+): Sharoon + Afsar + Arslan.
MAP_AMBASSADORS = {
    "Sharoon Javed": date(2026, 2, 11),
    "Afsar Khan": date(2026, 2, 16),
    "Arslan Ansari": date(2026, 2, 16),
}
EXPERIMENT_WINDOW_START = date(2026, 2, 11)
# No fixed end — uses today (excludes incomplete current day)

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
