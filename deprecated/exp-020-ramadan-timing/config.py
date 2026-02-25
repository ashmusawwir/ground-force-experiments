"""Experiment constants — the only file with hardcoded values."""

from datetime import date

EXPERIMENT_NAME = "Ramadan Visit Timing"
EXPERIMENT_START = date(2026, 2, 10)   # baseline start
RAMADAN_START = date(2026, 2, 19)

SHEET_ID = "1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ"
SHEET_TAB = "Form Responses 1"
TAGGING_TAB = "tagging"

# Column names (same sheet as show-dont-tell)
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

DEFAULT_CITY = "Karachi"

# ── Ramadan timing (hours as floats, e.g. 18.47 = 6:28pm) ──────────

CITY_TIMES = {
    "Karachi": {
        "iftar": 18.47,       # 6:28pm
        "isha": 19.67,        # 7:40pm
        "taraweeh_end": 21.5, # ~9:30pm
    },
    "Lahore": {
        "iftar": 17.88,       # 5:53pm
        "isha": 19.15,        # 7:09pm
        "taraweeh_end": 21.0, # ~9:00pm
    },
}

# Time bucket boundaries per city: list of (name, start_hour, end_hour)
# Hours are inclusive-start, exclusive-end.
CITY_BUCKETS = {
    "Karachi": [
        ("Briefing",         9.0,  11.5),
        ("Transit",         11.5,  12.5),
        ("Early Afternoon", 12.5,  15.0),
        ("Prime Daytime",   15.0,  17.0),
        ("Pre-Iftar Dead",  17.0,  18.5),
        ("Post-Iftar",      18.5,  19.67),
        ("During Taraweeh", 19.67, 21.5),
        ("Post-Taraweeh",   21.5,  24.0),
    ],
    "Lahore": [
        ("Briefing",         9.0,  11.5),
        ("Transit",         11.5,  12.5),
        ("Early Afternoon", 12.5,  14.5),
        ("Prime Daytime",   14.5,  16.0),
        ("Pre-Iftar Dead",  16.0,  17.83),
        ("Post-Iftar",      17.83, 19.15),
        ("During Taraweeh", 19.15, 21.0),
        ("Post-Taraweeh",   21.0,  24.0),
    ],
}

# Simplified two-window boundary: daytime vs nighttime
# "daytime" = before Iftar; "nighttime" = after Taraweeh end
# Visits in between (Iftar→Taraweeh) are classified as "evening_transition"
WINDOW_LABELS = ("Daytime", "Evening Transition", "Nighttime")

# Batch-logging detection threshold
BATCH_WINDOW_MINUTES = 5
BATCH_MIN_VISITS = 3
