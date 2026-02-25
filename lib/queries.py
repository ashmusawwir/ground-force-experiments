# lib/queries.py — Central query registry
# Every SQL query in the repo is importable from here.
# Uses importlib to load from hyphenated directory names.

import importlib.util
import os

_ROOT = os.path.join(os.path.dirname(__file__), '..')


def _load(rel, alias):
    p = os.path.normpath(os.path.join(_ROOT, rel))
    spec = importlib.util.spec_from_file_location(alias, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_q004 = _load('exp-004-merchant-activation/queries.py',  'q004')
_q006 = _load('exp-006-question-redirect/queries.py',    'q006')
_q007 = _load('exp-007-demo-dollars/queries.py',         'q007')
_q009 = _load('deprecated/exp-009-directed-day/queries.py', 'q009')
_qmuo = _load('exp-000-merchant-network/queries.py',     'qmuo')

# ── EXP-004: Merchant Activation Incentive ──────────────────────────────────
merchant_qualification_query   = _q004.merchant_qualification_query
distribution_summary_query     = _q004.distribution_summary_query
fraud_signals_query            = _q004.fraud_signals_query

# ── EXP-006: Question Redirect Protocol ─────────────────────────────────────
demo_onboarding_status_query   = _q006.demo_onboarding_status_query

# ── EXP-007: Demo Dollars ────────────────────────────────────────────────────
recipient_overview_query         = _q007.recipient_overview_query
note_distribution_query          = _q007.note_distribution_query
recipient_activity_query         = _q007.recipient_activity_query
ambassador_summary_query         = _q007.ambassador_summary_query
recipient_timing_query           = _q007.recipient_timing_query
demo_merchant_transactions_query = _q007.demo_merchant_transactions_query
time_to_first_tx_query           = _q007.time_to_first_tx_query
all_activity_timestamps_query    = _q007.all_activity_timestamps_query
note_detail_query                = _q007.note_detail_query

# ── EXP-009: Directed Day ────────────────────────────────────────────────────
reactivation_targets_query     = _q009.reactivation_targets_query
onboarding_status_check_query  = _q009.onboarding_status_check_query
onboarding_outcome_query       = _q009.onboarding_outcome_query
reactivation_outcome_query     = _q009.reactivation_outcome_query
pool_health_query              = _q009.pool_health_query

# ── EXP-000: Merchants Growing the ZAR Network ──────────────────────────────
merchant_summary_query          = _qmuo.merchant_summary_query
merchant_static_query           = _qmuo.merchant_static_query
user_onboardings_query          = _qmuo.user_onboardings_query
user_activations_query          = _qmuo.user_activations_query
merchant_daily_activity_query   = _qmuo.merchant_daily_activity_query
user_txn_breakdown_query        = _qmuo.user_txn_breakdown_query
user_invitations_query          = _qmuo.user_invitations_query
user_first_transactions_query   = _qmuo.user_first_transactions_query
user_cycling_query              = _qmuo.user_cycling_query
rapid_onboarding_query          = _qmuo.rapid_onboarding_query
cycling_timing_query            = _qmuo.cycling_timing_query
merchant_self_send_ring_query   = _qmuo.merchant_self_send_ring_query
merchant_fraud_summary_query    = _qmuo.merchant_fraud_summary_query
merchant_retention_query        = _qmuo.merchant_retention_query
cohort_analysis_query           = _qmuo.cohort_analysis_query
monthly_metrics_query           = _qmuo.monthly_metrics_query
daily_merchant_activity_query   = _qmuo.daily_merchant_activity_query
daily_overview_query            = _qmuo.daily_overview_query
