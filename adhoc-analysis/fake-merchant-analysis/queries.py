"""
SQL queries for fake merchant detection EDA.
Single source of truth — run via Rube MCP (METABASE_POST_API_DATASET, database=1).

All queries use PKT offset (+5h). Phase 1-7 mirrors the investigation structure
in findings.md.

Usage:
    from queries import mos_lookup_by_phone_query, ambassador_portfolio_query, ...

The flagged ambassador UUID used as a default parameter throughout is the
actual value identified during this investigation.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from lib.sql import EXCLUDED_IDS_SQL

# Ambassador UUID identified during this investigation
FLAGGED_AMBASSADOR_ID = '019c8ee0-c02c-75a0-ac4c-cf707f020d19'


# ---------------------------------------------------------------------------
# Phase 1: Profile the fakes + identify the ambassador
# ---------------------------------------------------------------------------

def mos_lookup_by_phone_query(phones=None):
    """Q1 — MOS record lookup by phone number.

    Returns form phone, account phone, onboarder identity, GPS, onboarding
    timestamp, and account-to-onboard latency for each matching MOS row.

    phones: list of E.164 phone strings. Defaults to the 4 phones with
    known-fake merchants identified by the verification team.
    """
    if phones is None:
        phones = ['+923122388838', '+923113263959', '+923090336070', '+923192713284']
    phone_list = ", ".join(f"'{p}'" for p in phones)
    return f"""
select
  mos.phone_number                                          as form_phone,
  u_m.phone_number                                         as account_phone,
  mos.phone_number = u_m.phone_number                      as phone_matches,
  mos.business_name, mos.status,
  mos.onboarder_id,
  u_onb.username                                           as onboarder_username,
  u_onb.phone_number                                       as onboarder_phone,
  mos.city, mos.latitude, mos.longitude,
  (mos.created_at + interval '5' hour)                     as onboarding_time_pkt,
  u_m.id                                                   as merchant_user_id,
  (u_m.created_at + interval '5' hour)                     as account_created_pkt,
  extract(epoch from (mos.created_at - u_m.created_at))/60 as mins_account_to_onboard
from merchant_onboarding_submissions mos
left join users u_onb on u_onb.id = mos.onboarder_id
left join users u_m   on u_m.phone_number = mos.phone_number
where mos.phone_number in ({phone_list})
"""


def mos_lookup_by_name_query(name_fragment):
    """Q2 — MOS record lookup by partial business name (case-insensitive LIKE).

    Use when the verification team's name doesn't match any phone in the DB,
    or when the phone field was left null in the form.

    name_fragment: substring to search, e.g. 'pakhtoon', 'hamza', 'hanif'.
    """
    return f"""
select mos.phone_number, mos.business_name, mos.status,
       mos.onboarder_id, u_onb.username as onboarder_username,
       mos.latitude, mos.longitude,
       (mos.created_at + interval '5' hour) as onboarding_time_pkt
from merchant_onboarding_submissions mos
left join users u_onb on u_onb.id = mos.onboarder_id
where lower(mos.business_name) like '%{name_fragment.lower()}%'
order by mos.created_at desc
limit 20
"""


def pe_lookup_by_phone_query(phones=None):
    """Q2b — PE-pathway merchant lookup by phone number.

    Since Dec 2023 (SHIP-2069), new merchants may onboard via product_enrollments
    instead of merchant_onboarding_submissions. MOS phone field may be null even
    when the user account has the real phone. This query finds those accounts.

    phones: list of E.164 phone strings.
    """
    if phones is None:
        phones = ['+923122388838', '+923113263959', '+923090336070', '+923192713284']
    phone_list = ", ".join(f"'{p}'" for p in phones)
    return f"""
select
  u.phone_number,
  u.username,
  pe.state,
  pd.code,
  (pe.created_at + interval '5' hour) as enrolled_pkt,
  u.id as user_id
from users u
join product_enrollments pe on pe.user_id = u.id
join product_definitions pd on pd.id = pe.product_definition_id
where u.phone_number in ({phone_list})
  and pd.code = 'zar_cash_exchange_merchant'
"""


# ---------------------------------------------------------------------------
# Phase 2: Ambassador's full onboarding portfolio
# ---------------------------------------------------------------------------

def ambassador_portfolio_query(ambassador_id=FLAGGED_AMBASSADOR_ID, since='2026-02-01'):
    """Q3 — All MOS submissions by the flagged ambassador since a given date.

    Returns business name, form phone vs account phone (match flag), status,
    GPS, timestamps, and account-to-onboard latency for each submission.
    """
    return f"""
select
  mos.business_name,
  mos.phone_number                                          as form_phone,
  u_m.phone_number                                         as account_phone,
  mos.phone_number = u_m.phone_number                      as phone_matches,
  mos.status, mos.city, mos.latitude, mos.longitude,
  (mos.created_at + interval '5' hour)                     as onboarding_time_pkt,
  u_m.id                                                   as merchant_user_id,
  (u_m.created_at + interval '5' hour)                     as account_created_pkt,
  extract(epoch from (mos.created_at - u_m.created_at))/60 as mins_account_to_onboard
from merchant_onboarding_submissions mos
left join users u_m on u_m.phone_number = mos.phone_number
where mos.onboarder_id = '{ambassador_id}'
  and mos.created_at >= '{since}'
order by mos.created_at
"""


def daily_onboarding_burst_query(since='2026-02-01', limit=30):
    """Q4 — Per-day onboarding submission count per ambassador (all ambassadors).

    Ordered by onboardings_that_day DESC to surface burst-day anomalies.
    A single ambassador holding the system-wide daily record is a fraud signal.
    """
    return f"""
select
  u_onb.username                                           as ambassador,
  (mos.created_at + interval '5' hour)::date               as onboarding_date,
  count(*)                                                  as onboardings_that_day
from merchant_onboarding_submissions mos
inner join users u_onb on u_onb.id = mos.onboarder_id
where mos.created_at >= '{since}'
group by u_onb.username, (mos.created_at + interval '5' hour)::date
order by onboardings_that_day desc
limit {limit}
"""


# ---------------------------------------------------------------------------
# Phase 3: Temporal signals
# ---------------------------------------------------------------------------

def inter_submission_gap_query(ambassador_id=FLAGGED_AMBASSADOR_ID, since='2026-02-01'):
    """Q5 — Time between consecutive MOS form submissions by the same ambassador.

    Uses a LAG window to compute mins_since_prev_submission. A gap of < 15 min
    between two submissions from the same person implies either machine-assisted
    form filling or pre-staged accounts. Sub-5-min gaps are definitive.
    """
    return f"""
select
  u_onb.username                                            as ambassador,
  mos.business_name,
  mos.phone_number,
  (mos.created_at + interval '5' hour)                      as submission_time_pkt,
  extract(epoch from (
    mos.created_at
    - lag(mos.created_at) over (partition by mos.onboarder_id order by mos.created_at)
  ))/60                                                     as mins_since_prev_submission
from merchant_onboarding_submissions mos
inner join users u_onb on u_onb.id = mos.onboarder_id
where mos.onboarder_id = '{ambassador_id}'
  and mos.created_at >= '{since}'
order by submission_time_pkt
"""


def account_age_buckets_query(since='2026-02-01'):
    """Q6 — Account age at time of merchant onboarding, all ambassadors (active/pending).

    Buckets: under_5min, under_1hr, under_1day, over_1day.
    Accounts onboarded within minutes of creation suggest the ambassador
    created the account themselves and immediately submitted the MOS form.
    Ordering ASC by mins_account_to_onboard surfaces the most suspicious rows.

    Scope: MOS-pathway only (inner join on phone). PE-pathway merchants are not
    captured here because their MOS phone field is typically null.
    """
    return f"""
select
  u_onb.username                                            as ambassador,
  mos.business_name, mos.phone_number,
  (mos.created_at + interval '5' hour)                      as onboarding_time_pkt,
  (u_m.created_at + interval '5' hour)                      as account_created_pkt,
  extract(epoch from (mos.created_at - u_m.created_at))/60  as mins_account_to_onboard,
  case
    when extract(epoch from (mos.created_at - u_m.created_at))/60 < 5   then 'under_5min'
    when extract(epoch from (mos.created_at - u_m.created_at))/60 < 60  then 'under_1hr'
    when extract(epoch from (mos.created_at - u_m.created_at))/60 < 1440 then 'under_1day'
    else 'over_1day'
  end                                                       as age_bucket
from merchant_onboarding_submissions mos
inner join users u_onb on u_onb.id = mos.onboarder_id
inner join users u_m   on u_m.phone_number = mos.phone_number
where mos.created_at >= '{since}'
  and mos.status in ('active', 'pending')
order by mins_account_to_onboard asc
"""


# ---------------------------------------------------------------------------
# Phase 4: GPS signals
# ---------------------------------------------------------------------------

def gps_velocity_query(ambassador_id=FLAGGED_AMBASSADOR_ID, since='2026-02-01'):
    """Q7 — GPS displacement between consecutive MOS form submissions (Haversine).

    km_from_prev: great-circle distance from previous submission's GPS coordinates.
    mins_from_prev: elapsed time between submissions.

    Flags to watch:
    - Large km_from_prev with small mins_from_prev: physically impossible travel.
    - All coordinates within < 500m across many days: submissions made from a
      single location (home/office) rather than real merchant visits.
    """
    return f"""
select
  u_onb.username                                           as ambassador,
  mos.business_name, mos.phone_number,
  mos.latitude, mos.longitude,
  (mos.created_at + interval '5' hour)                     as submission_time_pkt,
  round((6371 * acos(least(1.0,
    cos(radians(mos.latitude))
    * cos(radians(lag(mos.latitude) over (partition by mos.onboarder_id order by mos.created_at)))
    * cos(radians(lag(mos.longitude) over (partition by mos.onboarder_id order by mos.created_at))
        - radians(mos.longitude))
    + sin(radians(mos.latitude))
    * sin(radians(lag(mos.latitude) over (partition by mos.onboarder_id order by mos.created_at)))
  )))::numeric, 3)                                         as km_from_prev,
  extract(epoch from (
    mos.created_at
    - lag(mos.created_at) over (partition by mos.onboarder_id order by mos.created_at)
  ))/60                                                    as mins_from_prev
from merchant_onboarding_submissions mos
inner join users u_onb on u_onb.id = mos.onboarder_id
where mos.onboarder_id = '{ambassador_id}'
  and mos.created_at >= '{since}'
  and mos.latitude is not null and mos.longitude is not null
order by submission_time_pkt
"""


# ---------------------------------------------------------------------------
# Phase 5: Demo DCN signals
# ---------------------------------------------------------------------------

def dcn_claim_latency_query(ambassador_id=FLAGGED_AMBASSADOR_ID, since='2026-02-01'):
    """Q8 — Digital cash note claim latency for the flagged ambassador's demos.

    mins_to_claim: time from DCN creation to claim.
    Normal human claim latency: 30 sec – 5 min (merchant opens app, taps claim).
    Sub-30-second claims suggest the ambassador is claiming on behalf of the
    merchant (has access to the merchant's device or account) — strong fraud signal.
    Ordering ASC surfaces the fastest claims.
    """
    return f"""
select
  dcn.depositor_id                                         as ambassador_id,
  dcn.claimant_id                                          as merchant_user_id,
  u_m.phone_number,
  dcn.amount / 1e6                                         as demo_usd,
  (dcn.created_at  + interval '5' hour)                    as sent_time_pkt,
  (dcn.claimed_at  + interval '5' hour)                    as claimed_time_pkt,
  extract(epoch from (dcn.claimed_at - dcn.created_at))/60 as mins_to_claim
from digital_cash_notes dcn
inner join users u_m on u_m.id = dcn.claimant_id
where dcn.depositor_id = '{ambassador_id}'
  and dcn.status = 'claimed'
  and dcn.claimed_at is not null
  and (dcn.created_at + interval '5' hour)::date >= '{since}'
order by mins_to_claim asc
"""


def demo_before_onboard_query(ambassador_id=FLAGGED_AMBASSADOR_ID, since='2026-02-01'):
    """Q9 — Was a demo DCN claimed before the MOS submission for each merchant?

    had_demo_before_onboard: True if any DCN was claimed before the MOS record.
    mins_demo_before_onboard: how many minutes before (positive = demo came first).
    A merchant onboarded with no prior demo is suspicious — it suggests the
    onboarding was the goal, not the outcome of a demo visit.

    Scope: MOS-pathway merchants only (inner join on phone).
    PE-pathway merchants (null MOS phone) are not captured here — use a
    separate PE-aware query for those.
    """
    return f"""
with amb_merchants as (
  select mos.phone_number, mos.business_name,
         u_m.id                 as merchant_user_id,
         mos.created_at         as onboarding_at
  from merchant_onboarding_submissions mos
  inner join users u_m on u_m.phone_number = mos.phone_number
  where mos.onboarder_id = '{ambassador_id}'
    and mos.created_at >= '{since}'
)
select
  am.phone_number, am.business_name,
  (am.onboarding_at + interval '5' hour)                   as onboarding_time_pkt,
  count(dcn.id)                                            as dcn_count,
  max(dcn.amount / 1e6)                                    as max_demo_usd,
  max((dcn.claimed_at + interval '5' hour))                as last_demo_pkt,
  extract(epoch from (
    am.onboarding_at - max(dcn.claimed_at)
  ))/60                                                    as mins_demo_before_onboard,
  count(dcn.id) > 0                                        as had_demo_before_onboard
from amb_merchants am
left join digital_cash_notes dcn
  on dcn.claimant_id = am.merchant_user_id
  and dcn.status = 'claimed'
  and dcn.claimed_at < am.onboarding_at
group by am.phone_number, am.business_name, am.onboarding_at
order by had_demo_before_onboard, am.onboarding_at
"""


# ---------------------------------------------------------------------------
# Phase 6: Post-onboarding activity
# ---------------------------------------------------------------------------

def flagged_merchant_transactions_query(phones=None):
    """Q10 — All completed transactions for users matching flagged phone numbers.

    Checks for any real merchant activity (Transaction::CashExchange as merchant)
    vs exclusively demo-related activity (DigitalCashClaim, BankTransfer of
    exactly the demo amount). Zero CashExchange merchant rows = no real usage.
    """
    if phones is None:
        phones = ['+923122388838', '+923113263959', '+923090336070', '+923192713284']
    phone_list = ", ".join(f"'{p}'" for p in phones)
    return f"""
select
  u.phone_number, u.username,
  t.type, t.amount / 1e6 as amount_usd, t.status,
  (t.created_at + interval '5' hour)::date as txn_date
from users u
left join transactions t on t.user_id = u.id and t.status = 3
where u.phone_number in ({phone_list})
order by u.phone_number, txn_date
"""


def post_onboard_activity_buckets_query(since='2026-02-01'):
    """Q11 — Post-onboarding CashExchange activity buckets, all MOS ambassadors.

    Buckets: day 0-1, day 2-7, day 8-30 after onboarding.
    zero_activity: merchant never made a single CashExchange transaction.

    Scope: MOS-pathway merchants only (inner join on phone). Useful for
    comparing the flagged ambassador's zero-activity rate against peers.

    An ambassador with 100% zero-activity merchants is a strong fraud signal,
    especially when combined with other signals.
    """
    return f"""
with m as (
  select u.id as merchant_id, u.phone_number,
         mos.onboarder_id,
         mos.created_at as onboarding_at
  from merchant_onboarding_submissions mos
  inner join users u on u.phone_number = mos.phone_number
  where mos.created_at >= '{since}'
    and mos.status in ('active','pending')
),
buckets as (
  select m.merchant_id, m.onboarder_id,
    count(t.id) filter (
      where t.created_at between m.onboarding_at and m.onboarding_at + interval '1 day'
    ) as txns_day0_1,
    count(t.id) filter (
      where t.created_at > m.onboarding_at + interval '1 day'
       and t.created_at <= m.onboarding_at + interval '7 days'
    ) as txns_day2_7,
    count(t.id) filter (
      where t.created_at > m.onboarding_at + interval '7 days'
       and t.created_at <= m.onboarding_at + interval '30 days'
    ) as txns_day8_30
  from m
  left join transactions t
    on t.user_id = m.merchant_id
    and t.type = 'Transaction::CashExchange'
    and t.status = 3
    and t.metadata->>'role' = 'merchant'
  group by m.merchant_id, m.onboarder_id
)
select
  u_onb.username                                           as ambassador,
  count(*)                                                 as total_merchants,
  count(*) filter (where txns_day0_1 > 0)                 as active_d0_1,
  count(*) filter (where txns_day2_7 > 0)                 as active_d2_7,
  count(*) filter (where txns_day8_30 > 0)                as active_d8_30,
  count(*) filter (where txns_day0_1 = 0 and txns_day2_7 = 0 and txns_day8_30 = 0) as zero_activity
from buckets b
inner join users u_onb on u_onb.id = b.onboarder_id
group by u_onb.username
order by zero_activity desc
"""


# ---------------------------------------------------------------------------
# Phase 7: Phone number signals
# ---------------------------------------------------------------------------

def phone_prefix_distribution_query(ambassador_id=FLAGGED_AMBASSADOR_ID, since='2026-02-01'):
    """Q12 — Phone number prefix distribution for the flagged ambassador's portfolio.

    Extracts the first 7 characters of the form phone (includes country code +92
    plus 4-digit carrier prefix). A cluster of identical prefixes — especially
    on a sequential range — suggests fabricated numbers from a single number block.

    Note: 12/14 submissions in this investigation had null form phone. The signal
    fires on the null rate itself, not on prefix patterns. Retain this query for
    future investigations where phones are present.
    """
    return f"""
select
  mos.phone_number,
  mos.business_name,
  substring(mos.phone_number, 1, 7)                        as prefix_6digit,
  (mos.created_at + interval '5' hour)                     as onboarding_time_pkt
from merchant_onboarding_submissions mos
where mos.onboarder_id = '{ambassador_id}'
  and mos.created_at >= '{since}'
order by mos.phone_number
"""


# ---------------------------------------------------------------------------
# Population-Level Validation (PA1–PA3)
# ---------------------------------------------------------------------------

def fleet_dcn_latency_query(since='2026-02-01'):
    """PA1 — Fleet-wide DCN claim latency distribution per ambassador.

    For every ambassador who sent demo DCNs since the given date, shows their
    latency bucket distribution and pct_sub_2min. Used to assess whether
    sub-2-min claims are an ilyas_khan anomaly or common across all ambassadors.

    If sub-2-min is common fleet-wide, the signal has high false-positive risk.
    If ilyas_khan is a clear outlier, the threshold is defensible.
    """
    return f"""
with amb as (
    select distinct uur.user_id as ambassador_id
    from user_to_user_roles uur
    inner join user_roles ur on ur.id = uur.user_role_id
    where ur.name = 'ambassador'
)
select
    u.username                                                                    as ambassador,
    count(*)                                                                      as total_demos,
    round(min(extract(epoch from (dcn.claimed_at - dcn.created_at))/60)::numeric, 2)
                                                                                  as fastest_claim_min,
    round(cast(percentile_cont(0.5) within group (
        order by extract(epoch from (dcn.claimed_at - dcn.created_at))/60
    ) as numeric), 2)                                                             as median_claim_min,
    count(*) filter (where extract(epoch from (dcn.claimed_at - dcn.created_at))/60 < 1)
                                                                                  as sub_1min,
    count(*) filter (where extract(epoch from (dcn.claimed_at - dcn.created_at))/60 between 1 and 2)
                                                                                  as one_to_2min,
    count(*) filter (where extract(epoch from (dcn.claimed_at - dcn.created_at))/60 between 2 and 5)
                                                                                  as two_to_5min,
    count(*) filter (where extract(epoch from (dcn.claimed_at - dcn.created_at))/60 > 5)
                                                                                  as over_5min,
    round(100.0 * count(*) filter (
        where extract(epoch from (dcn.claimed_at - dcn.created_at))/60 < 2
    ) / count(*), 1)                                                              as pct_sub_2min
from digital_cash_notes dcn
inner join amb a on a.ambassador_id = dcn.depositor_id
inner join users u on u.id = dcn.depositor_id
where dcn.status = 'claimed'
  and dcn.claimed_at is not null
  and (dcn.created_at + interval '5' hour)::date >= '{since}'
group by u.username
order by pct_sub_2min desc
"""


def merchant_signal_profile_query(since='2026-02-01'):
    """PA2 — Per-merchant signal profile for all PE-enrolled merchants since the given date.

    One row per merchant. Computes all PE-era fraud signals in a single query:
    - mins_acct_to_enroll: account age at PE enrollment (acct_age_bucket)
    - fastest_dcn_min: minimum claim latency across all demo DCNs sent to this merchant
    - dcn_sub_2min: whether the fastest claim was under 2 minutes
    - txns_30d: CashExchange merchant transactions in the 30 days post-enrollment
    - zero_activity: whether txns_30d == 0
    - fraud_score: composite 0-3 (sub-2-min DCN + acct under 1hr + zero activity)

    The 5 known fakes should cluster at fraud_score=3 at the top of the result.
    The question is what else surfaces at score ≥ 2.
    """
    return f"""
with pe_merchants as (
    select
        pe.user_id                                                                as merchant_id,
        u.phone_number,
        u.created_at                                                              as account_created_at,
        pe.created_at                                                             as enrolled_at,
        extract(epoch from (pe.created_at - u.created_at))/60                    as mins_acct_to_enroll
    from product_enrollments pe
    inner join product_definitions pd on pd.id = pe.product_definition_id
    inner join users u on u.id = pe.user_id
    where pd.code = 'zar_cash_exchange_merchant'
      and pe.state = 2
      and pe.created_at >= '{since}'
),
demo as (
    select distinct on (dcn.claimant_id)
        dcn.claimant_id                                                           as merchant_id,
        dcn.depositor_id                                                          as ambassador_id,
        u_amb.username                                                            as ambassador,
        extract(epoch from (dcn.claimed_at - dcn.created_at))/60                 as mins_to_claim
    from digital_cash_notes dcn
    inner join users u_amb on u_amb.id = dcn.depositor_id
    inner join user_to_user_roles uur on uur.user_id = dcn.depositor_id
    inner join user_roles ur on ur.id = uur.user_role_id and ur.name = 'ambassador'
    where dcn.status = 'claimed'
      and dcn.claimed_at is not null
    order by dcn.claimant_id, mins_to_claim asc
),
activity as (
    select
        t.user_id                                                                 as merchant_id,
        count(*)                                                                  as txn_count_30d
    from transactions t
    inner join pe_merchants pm on pm.merchant_id = t.user_id
    where t.type = 'Transaction::CashExchange'
      and t.status = 3
      and t.metadata->>'role' = 'merchant'
      and t.created_at between pm.enrolled_at and pm.enrolled_at + interval '30 days'
    group by t.user_id
)
select
    pm.phone_number,
    d.ambassador,
    round(pm.mins_acct_to_enroll::numeric, 1)                                    as mins_acct_to_enroll,
    case
        when pm.mins_acct_to_enroll < 5    then 'under_5min'
        when pm.mins_acct_to_enroll < 60   then 'under_1hr'
        when pm.mins_acct_to_enroll < 1440 then 'under_1day'
        else 'over_1day'
    end                                                                           as acct_age_bucket,
    round(d.mins_to_claim::numeric, 2)                                            as fastest_dcn_min,
    case when d.mins_to_claim < 2 then true else false end                        as dcn_sub_2min,
    coalesce(a.txn_count_30d, 0)                                                  as txns_30d,
    case when coalesce(a.txn_count_30d, 0) = 0 then true else false end           as zero_activity,
    (case when d.mins_to_claim < 2      then 1 else 0 end
     + case when pm.mins_acct_to_enroll < 60 then 1 else 0 end
     + case when coalesce(a.txn_count_30d, 0) = 0 then 1 else 0 end)             as fraud_score
from pe_merchants pm
left join demo d on d.merchant_id = pm.merchant_id
left join activity a on a.merchant_id = pm.merchant_id
order by fraud_score desc, fastest_dcn_min asc nulls last
"""


def ambassador_name_query(ambassador_id=FLAGGED_AMBASSADOR_ID):
    """QN-1 — Resolve an ambassador's first/last name from their user UUID.

    Used to match ambassador identity against visit sheet "Ambassador Name"
    free-text column. Returns empty strings if the user has no name set.
    """
    return f"""
SELECT first_name, last_name, username, phone_number
FROM users
WHERE id = '{ambassador_id}'
"""


def fake_merchant_user_ids_query(phones=None):
    """QN-2 — Resolve PE-pathway merchant user IDs and enrollment timestamps
    for a list of known-fake phone numbers.

    Returns user_id, phone, and enrolled_at_pkt for each phone that has an
    active (state=2) product enrollment for the merchant product code.
    Used to seed Amplitude app-open checks.

    phones: list of E.164 strings. Defaults to the 4 confirmed fake phones.
    """
    if phones is None:
        phones = ['+923122388838', '+923113263959', '+923090336070', '+923192713284']
    phone_list = ", ".join(f"'{p}'" for p in phones)
    return f"""
SELECT
  u.id                                                              AS user_id,
  u.phone_number,
  u.first_name,
  u.last_name,
  (pe.created_at + interval '5' hour)                             AS enrolled_at_pkt
FROM users u
JOIN product_enrollments pe ON pe.user_id = u.id
JOIN product_definitions pd ON pd.id = pe.product_definition_id
WHERE u.phone_number IN ({phone_list})
  AND pd.code = 'zar_cash_exchange_merchant'
  AND pe.state = 2
"""


def ilyas_pe_cohort_query(ambassador_id=FLAGGED_AMBASSADOR_ID, since='2026-02-01'):
    """QN-3 — All PE-enrolled merchants who received a DCN from the flagged
    ambassador since the given date.

    Identifies the full PE-pathway merchant cohort for this ambassador even
    when no MOS form was filed. Uses the DCN depositor_id as the ambassador
    proxy (whoever sent the demo DCN is treated as the onboarding ambassador).

    Returns user_id, phone, and enrolled_at_pkt for each distinct merchant.
    """
    return f"""
SELECT DISTINCT
  u.id                                                              AS user_id,
  u.phone_number,
  u.first_name,
  u.last_name,
  (pe.created_at + interval '5' hour)                             AS enrolled_at_pkt
FROM product_enrollments pe
JOIN product_definitions pd ON pd.id = pe.product_definition_id
JOIN users u ON u.id = pe.user_id
WHERE pd.code = 'zar_cash_exchange_merchant'
  AND pe.state = 2
  AND pe.created_at >= '{since}'
  AND pe.user_id IN (
    SELECT DISTINCT dcn.claimant_id
    FROM digital_cash_notes dcn
    WHERE dcn.depositor_id = '{ambassador_id}'
      AND dcn.status = 'claimed'
  )
ORDER BY enrolled_at_pkt
"""


def enrollment_dcn_timing_query(merchant_id, ambassador_id=FLAGGED_AMBASSADOR_ID):
    """Q-X1 — Targeted enrollment-vs-DCN timing for a single PE merchant.

    Compares the DCN send/claim timestamps from the flagged ambassador against
    the PE enrollment timestamp for the specified merchant.

    mins_enroll_after_dcn_sent:    positive = normal (enroll after DCN sent)
                                   negative = PRE_STAGED (enroll before DCN sent)
    mins_enroll_after_dcn_claimed: positive = normal
                                   negative = enrolled between send and claim

    First used for hamza dot com (2026-02-28): returned +5.55 min (NORMAL).
    The anomaly for hamza is enrollment before the physical demo visit, not
    before the DCN — which is a separate signal not captured here.
    """
    return f"""
SELECT
  dcn.id,
  dcn.amount / 1e6 AS demo_usd,
  (dcn.created_at  + interval '5' hour) AS sent_pkt,
  (dcn.claimed_at  + interval '5' hour) AS claimed_pkt,
  (pe.created_at   + interval '5' hour) AS enrolled_pkt,
  ROUND(EXTRACT(EPOCH FROM (pe.created_at - dcn.created_at))/60::numeric, 2)  AS mins_enroll_after_dcn_sent,
  ROUND(EXTRACT(EPOCH FROM (pe.created_at - dcn.claimed_at))/60::numeric, 2)  AS mins_enroll_after_dcn_claimed
FROM digital_cash_notes dcn
JOIN product_enrollments pe ON pe.user_id = dcn.claimant_id
JOIN product_definitions pd ON pd.id = pe.product_definition_id
WHERE dcn.claimant_id = '{merchant_id}'
  AND dcn.depositor_id = '{ambassador_id}'
  AND pd.code = 'zar_cash_exchange_merchant'
  AND pe.state = 2
  AND dcn.status = 'claimed'
"""


def enrollment_vs_dcn_fleet_query(since='2026-02-01'):
    """Q-X2 — Fleet-wide enrollment-vs-DCN sequence classification.

    For every PE merchant who received a demo DCN from an ambassador, classifies
    the enrollment sequence as:
      PRE_STAGED:                   enrolled BEFORE DCN was sent (ambassador staged
                                    the account before the demo)
      ENROLLED_BETWEEN_SEND_AND_CLAIM: enrolled after DCN sent but before claim
      NORMAL:                       enrolled after DCN was claimed

    Fleet result (109 merchants, Feb 1+): 5 PRE_STAGED (4.6%), 104 NORMAL.
    PRE_STAGED ambassadors: owaisferoz1 (2/20), ilyas_khan (1/10), user_1ef1d1ea
    (1/23), turab (1/2). NOT unique to ilyas_khan — a minority pattern fleet-wide.
    ilyas_khan's PRE_STAGED merchant: gujjar dot com (-8.3 mins).
    """
    return f"""
WITH pe_merchants AS (
  SELECT pe.user_id AS merchant_id,
         (pe.created_at + interval '5' hour) AS enrolled_pkt,
         pe.created_at AS enrolled_at
  FROM product_enrollments pe
  JOIN product_definitions pd ON pd.id = pe.product_definition_id
  WHERE pd.code = 'zar_cash_exchange_merchant'
    AND pe.state = 2
    AND pe.created_at >= '{since}'
),
first_dcn AS (
  SELECT dcn.claimant_id AS merchant_id,
         MIN(dcn.created_at) AS first_dcn_sent_at,
         MIN(dcn.claimed_at) AS first_dcn_claimed_at,
         u_amb.username AS ambassador
  FROM digital_cash_notes dcn
  JOIN user_to_user_roles uur ON uur.user_id = dcn.depositor_id
  JOIN user_roles ur ON ur.id = uur.user_role_id AND ur.name = 'ambassador'
  JOIN users u_amb ON u_amb.id = dcn.depositor_id
  WHERE dcn.status = 'claimed'
  GROUP BY dcn.claimant_id, u_amb.username
)
SELECT
  u.phone_number,
  fd.ambassador,
  pm.enrolled_pkt,
  (fd.first_dcn_sent_at   + interval '5' hour) AS first_dcn_sent_pkt,
  (fd.first_dcn_claimed_at + interval '5' hour) AS first_dcn_claimed_pkt,
  ROUND(EXTRACT(EPOCH FROM (pm.enrolled_at - fd.first_dcn_sent_at))/60::numeric, 1) AS mins_enroll_after_dcn_sent,
  CASE
    WHEN pm.enrolled_at < fd.first_dcn_sent_at THEN 'PRE_STAGED'
    WHEN pm.enrolled_at < fd.first_dcn_claimed_at THEN 'ENROLLED_BETWEEN_SEND_AND_CLAIM'
    ELSE 'NORMAL'
  END AS sequence
FROM pe_merchants pm
JOIN first_dcn fd ON fd.merchant_id = pm.merchant_id
JOIN users u ON u.id = pm.merchant_id
ORDER BY mins_enroll_after_dcn_sent ASC
"""


def demo_cashout_signal_query(since='2026-02-01'):
    """PA5 — Per-merchant immediate bank transfer after DCN claim.

    Detects merchants who claimed a demo DCN from an ambassador and then
    immediately did a BankTransfer of a similar amount (±20%) within 48 hours.
    This was originally hypothesized as the cleanest behavioral fraud signal.

    Fleet result (Feb 1+): 29 merchants across 9 ambassadors cashed out.
    ilyas_khan: 2/10 merchants (20%) — BELOW median, not an outlier.
    Highest rates: irfan1 (67%), mighty_robin_3902 (50%), owaisferoz1 (45%).
    Signal does NOT discriminate ilyas_khan from peers.

    Note: Only 2 of 4 confirmed fakes appear in the 48h window (gujjar at 0.1h,
    sr_comm at 0.7h). hanif and hamza either transferred outside 48h or at
    different amounts — reducing signal completeness.
    """
    return f"""
WITH demo_dcns AS (
  SELECT
    dcn.claimant_id AS merchant_id,
    u_amb.username  AS ambassador,
    dcn.amount      AS demo_amount,
    dcn.claimed_at  AS claimed_at
  FROM digital_cash_notes dcn
  JOIN user_to_user_roles uur ON uur.user_id = dcn.depositor_id
  JOIN user_roles ur ON ur.id = uur.user_role_id AND ur.name = 'ambassador'
  JOIN users u_amb ON u_amb.id = dcn.depositor_id
  JOIN product_enrollments pe ON pe.user_id = dcn.claimant_id
  JOIN product_definitions pd ON pd.id = pe.product_definition_id
  WHERE dcn.status = 'claimed'
    AND dcn.claimed_at IS NOT NULL
    AND pd.code = 'zar_cash_exchange_merchant'
    AND pe.state = 2
    AND pe.created_at >= '{since}'
),
immediate_cashout AS (
  SELECT
    d.merchant_id,
    d.ambassador,
    d.demo_amount,
    d.claimed_at,
    t.created_at AS transfer_at,
    t.amount     AS transfer_amount,
    EXTRACT(EPOCH FROM (t.created_at - d.claimed_at))/3600 AS hrs_to_cashout
  FROM demo_dcns d
  JOIN transactions t ON t.user_id = d.merchant_id
    AND t.type = 'Transaction::BankTransfer'
    AND t.status = 3
    AND t.amount BETWEEN d.demo_amount * 0.8 AND d.demo_amount * 1.2
    AND t.created_at BETWEEN d.claimed_at AND d.claimed_at + INTERVAL '48 hours'
)
SELECT
  u.phone_number,
  ic.ambassador,
  ROUND((ic.demo_amount / 1e6)::numeric, 2)     AS demo_usd,
  ROUND((ic.transfer_amount / 1e6)::numeric, 2) AS cashout_usd,
  ROUND(ic.hrs_to_cashout::numeric, 1)          AS hrs_to_cashout,
  (ic.claimed_at + interval '5' hour)  AS claimed_pkt,
  (ic.transfer_at + interval '5' hour) AS cashout_pkt
FROM immediate_cashout ic
JOIN users u ON u.id = ic.merchant_id
ORDER BY ic.hrs_to_cashout ASC
"""


def ambassador_cashout_summary_query(since='2026-02-01'):
    """PA5 rollup — Per-ambassador immediate cashout rate.

    Aggregates demo_cashout_signal_query() to the ambassador level. Shows
    what fraction of each ambassador's PE merchant cohort cashed out within
    48h of claiming the demo DCN.

    Fleet result: median ~25%, range 0-67%. ilyas_khan at 20% is unremarkable.
    This signal has no discriminating power for ilyas_khan specifically.
    """
    return f"""
WITH demo_dcns AS (
  SELECT
    dcn.claimant_id AS merchant_id,
    u_amb.username  AS ambassador,
    dcn.amount      AS demo_amount,
    dcn.claimed_at  AS claimed_at
  FROM digital_cash_notes dcn
  JOIN user_to_user_roles uur ON uur.user_id = dcn.depositor_id
  JOIN user_roles ur ON ur.id = uur.user_role_id AND ur.name = 'ambassador'
  JOIN users u_amb ON u_amb.id = dcn.depositor_id
  JOIN product_enrollments pe ON pe.user_id = dcn.claimant_id
  JOIN product_definitions pd ON pd.id = pe.product_definition_id
  WHERE dcn.status = 'claimed'
    AND dcn.claimed_at IS NOT NULL
    AND pd.code = 'zar_cash_exchange_merchant'
    AND pe.state = 2
    AND pe.created_at >= '{since}'
),
immediate_cashout AS (
  SELECT
    d.merchant_id,
    d.ambassador,
    d.demo_amount,
    d.claimed_at,
    t.created_at AS transfer_at,
    t.amount     AS transfer_amount,
    EXTRACT(EPOCH FROM (t.created_at - d.claimed_at))/3600 AS hrs_to_cashout
  FROM demo_dcns d
  JOIN transactions t ON t.user_id = d.merchant_id
    AND t.type = 'Transaction::BankTransfer'
    AND t.status = 3
    AND t.amount BETWEEN d.demo_amount * 0.8 AND d.demo_amount * 1.2
    AND t.created_at BETWEEN d.claimed_at AND d.claimed_at + INTERVAL '48 hours'
)
SELECT
  d.ambassador,
  COUNT(DISTINCT d.merchant_id)  AS total_demo_merchants,
  COUNT(DISTINCT ic.merchant_id) AS cashout_within_48h,
  ROUND(100.0 * COUNT(DISTINCT ic.merchant_id) / NULLIF(COUNT(DISTINCT d.merchant_id), 0), 0) AS pct_immediate_cashout,
  ROUND(AVG(ic.hrs_to_cashout)::numeric, 1) AS avg_hrs_to_cashout
FROM demo_dcns d
LEFT JOIN immediate_cashout ic ON ic.merchant_id = d.merchant_id
GROUP BY d.ambassador
ORDER BY pct_immediate_cashout DESC NULLS LAST
"""


def ambassador_risk_summary_query(since='2026-02-01'):
    """PA3 — Ambassador-level fraud signal summary for all Feb 1+ ambassadors.

    Aggregates PA2 signals per ambassador: what % of each ambassador's PE merchant
    cohort triggers each signal. Ranks by weighted_risk_score.

    weighted_risk_score: (2 × dcn_sub_2min + acct_under_1hr + zero_activity) / total_merchants
    DCN latency gets 2× weight as the most reliable signal.

    Only includes ambassadors with ≥ 2 PE merchants in the window.
    """
    return f"""
with pe_merchants as (
    select
        pe.user_id                                                                as merchant_id,
        pe.created_at                                                             as enrolled_at,
        extract(epoch from (pe.created_at - u.created_at))/60                    as mins_acct_to_enroll
    from product_enrollments pe
    inner join product_definitions pd on pd.id = pe.product_definition_id
    inner join users u on u.id = pe.user_id
    where pd.code = 'zar_cash_exchange_merchant'
      and pe.state = 2
      and pe.created_at >= '{since}'
),
demo as (
    select distinct on (dcn.claimant_id)
        dcn.claimant_id                                                           as merchant_id,
        dcn.depositor_id                                                          as ambassador_id,
        extract(epoch from (dcn.claimed_at - dcn.created_at))/60                 as mins_to_claim
    from digital_cash_notes dcn
    inner join user_to_user_roles uur on uur.user_id = dcn.depositor_id
    inner join user_roles ur on ur.id = uur.user_role_id and ur.name = 'ambassador'
    where dcn.status = 'claimed'
      and dcn.claimed_at is not null
    order by dcn.claimant_id, mins_to_claim asc
),
activity as (
    select
        t.user_id                                                                 as merchant_id,
        count(*)                                                                  as txn_count_30d
    from transactions t
    inner join pe_merchants pm on pm.merchant_id = t.user_id
    where t.type = 'Transaction::CashExchange'
      and t.status = 3
      and t.metadata->>'role' = 'merchant'
      and t.created_at between pm.enrolled_at and pm.enrolled_at + interval '30 days'
    group by t.user_id
),
scored as (
    select
        d.ambassador_id,
        pm.merchant_id,
        d.mins_to_claim,
        pm.mins_acct_to_enroll,
        coalesce(a.txn_count_30d, 0)                                              as txns_30d
    from pe_merchants pm
    left join demo d on d.merchant_id = pm.merchant_id
    left join activity a on a.merchant_id = pm.merchant_id
)
select
    u.username                                                                    as ambassador,
    count(*)                                                                      as total_merchants,
    count(*) filter (where mins_to_claim < 2)                                     as dcn_sub_2min,
    count(*) filter (where mins_acct_to_enroll < 60)                              as acct_under_1hr,
    count(*) filter (where txns_30d = 0)                                          as zero_activity,
    round(100.0 * count(*) filter (where mins_to_claim < 2) / count(*), 0)       as pct_dcn_sub_2min,
    round(100.0 * count(*) filter (where txns_30d = 0) / count(*), 0)            as pct_zero_activity,
    round((
        2.0 * count(*) filter (where mins_to_claim < 2)
        + 1.0 * count(*) filter (where mins_acct_to_enroll < 60)
        + 1.0 * count(*) filter (where txns_30d = 0)
    ) / count(*), 2)                                                              as weighted_risk_score
from scored s
inner join users u on u.id = s.ambassador_id
group by u.username
having count(*) >= 2
order by weighted_risk_score desc
"""


# ---------------------------------------------------------------------------
# PA7 — Ambassador Behavioral Signals (Next-Generation Fraud Detection)
# ---------------------------------------------------------------------------
# Core insight: every PA1–PA6 signal measured *merchant* behavior. The fraud
# is ambassador-side. New signals measure *ambassador behavioral anomalies*
# across their portfolio, not any individual merchant's profile.
#
# Sources: Terra (field ops), Nash (game theory), FIELD_FRAUD researcher,
# WEB_RESEARCH (GSMA 2024, MicroSave, Featurespace, Finextra).
# ---------------------------------------------------------------------------


def dcn_burst_pattern_query(since='2026-02-01'):
    """PA7-B — Per-ambassador DCN send temporal clustering (desk-sending detector).

    Real field work is rate-limited by travel (~15–30 min per merchant visit).
    Sending 3+ DCNs to different merchants within 20 minutes means the sender
    never moved — they were operating from a desk.

    Computes the maximum DCNs sent by an ambassador within any rolling
    20-minute window, per day. Fleet-wide — not just the flagged ambassador.

    Flag rule: max_dcns_in_20min >= 3 on any day warrants review.
    Fleet comparison: is ilyas_khan's burst pattern unique or common?

    Sources: Nash (desk-sending is the rational strategy when detection cost
    is low), GSMA 2024.
    """
    return f"""
WITH dcn_bursts AS (
    SELECT
        u_amb.username                                              AS ambassador,
        (dcn.created_at + INTERVAL '5 hours')::date               AS day_pkt,
        (dcn.created_at + INTERVAL '5 hours')                     AS sent_pkt,
        dcn.claimant_id,
        COUNT(*) OVER (
            PARTITION BY dcn.depositor_id
            ORDER BY dcn.created_at
            RANGE BETWEEN INTERVAL '20 minutes' PRECEDING AND CURRENT ROW
        )                                                          AS dcns_in_20min_window
    FROM digital_cash_notes dcn
    JOIN user_to_user_roles uur ON uur.user_id = dcn.depositor_id
    JOIN user_roles ur ON ur.id = uur.user_role_id AND ur.name = 'ambassador'
    JOIN users u_amb ON u_amb.id = dcn.depositor_id
    WHERE dcn.status = 'claimed'
      AND dcn.created_at >= '{since}'
)
SELECT
    ambassador,
    day_pkt,
    COUNT(*)                                                       AS total_dcns_that_day,
    MAX(dcns_in_20min_window)                                      AS max_dcns_in_20min,
    COUNT(*) FILTER (WHERE dcns_in_20min_window >= 3)             AS dcns_in_burst_events,
    CASE WHEN MAX(dcns_in_20min_window) >= 3
         THEN 'BURST_FLAGGED' ELSE 'normal' END                   AS flag
FROM dcn_bursts
GROUP BY ambassador, day_pkt
ORDER BY max_dcns_in_20min DESC, total_dcns_that_day DESC
"""


def visit_enrollment_ratio_query(since='2026-02-01'):
    """PA7-C/D — DB side of the Visit-to-Enrollment Ratio (VER) and
    cross-attribution fleet map.

    Returns PE enrollment counts per ambassador (DB side only).
    Full VER = pe_enrollments / distinct_merchants_visited (visit sheet side).

    To compute full VER + cross-attribution (requires Rube workbench):
    1. Run this query via Metabase → get per-ambassador enrollment counts.
    2. Fetch visit sheet (ID: 1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ,
       tab: Visits) via Rube Google Sheets.
    3. Join on merchant phone number in the workbench.
    4. Flag rule A (VER): enrollments / visits > 1.5 = suspicious.
    5. Flag rule B (cross-attribution): >20% of ambassador's PE merchants were
       physically visited by a *different* ambassador within ±48h of enrollment.

    ilyas_khan baseline: 10 PE enrollments, 1 logged visit = VER 0.10 (extreme).
    Expected VER for honest ambassadors: 0.3–0.8 (not every visited merchant enrolls).

    Sources: Nash, Terra.
    """
    return f"""
SELECT
    u_amb.username                                                 AS ambassador,
    COUNT(DISTINCT pe.user_id)                                     AS pe_enrollments,
    COUNT(DISTINCT u_m.phone_number)
        FILTER (WHERE u_m.phone_number IS NOT NULL)                AS enrollments_with_phone,
    MIN((pe.created_at + INTERVAL '5 hours'))                      AS earliest_enrollment_pkt,
    MAX((pe.created_at + INTERVAL '5 hours'))                      AS latest_enrollment_pkt
FROM product_enrollments pe
JOIN product_definitions pd ON pd.id = pe.product_definition_id
JOIN digital_cash_notes dcn ON dcn.claimant_id = pe.user_id
    AND dcn.status = 'claimed'
JOIN user_to_user_roles uur ON uur.user_id = dcn.depositor_id
JOIN user_roles ur ON ur.id = uur.user_role_id AND ur.name = 'ambassador'
JOIN users u_amb ON u_amb.id = dcn.depositor_id
JOIN users u_m ON u_m.id = pe.user_id
WHERE pd.code = 'zar_cash_exchange_merchant'
  AND pe.state = 2
  AND pe.created_at >= '{since}'
GROUP BY u_amb.username
ORDER BY pe_enrollments DESC
"""


def enrollment_timing_variance_query(since='2026-02-01', ambassador_id=None):
    """PA7-E — PE enrollment inter-arrival time variance per ambassador per day.

    Legitimate field days have high inter-arrival variance (some merchants take
    5 min, some 40 min). Batch desk processing has low variance — regular
    clockwork intervals every 8–10 min.

    Computes the coefficient of variation (CV = stddev/mean) of inter-
    enrollment gaps per ambassador per day. Requires ≥4 enrollments in a day
    (3+ measurable gaps).

    Flag rule: CV < 0.3 with ≥5 enrollments/day = automation signal.
    Reference: Poisson process CV = 1.0; human field behavior CV ~0.5–2.0;
    mechanical batch CV → 0.

    ambassador_id: if set, filters to that ambassador only. Default: fleet-wide.

    Sources: Terra (field ops timing), FIELD_FRAUD researcher.
    """
    amb_filter = f"AND dcn.depositor_id = '{ambassador_id}'" if ambassador_id else ""
    return f"""
WITH pe_ambassadors AS (
    SELECT
        dcn.depositor_id                                           AS ambassador_id,
        u_amb.username                                             AS ambassador,
        pe.created_at                                              AS enrolled_at,
        (pe.created_at + INTERVAL '5 hours')::date                AS enroll_day
    FROM product_enrollments pe
    JOIN product_definitions pd ON pd.id = pe.product_definition_id
    JOIN digital_cash_notes dcn ON dcn.claimant_id = pe.user_id
        AND dcn.status = 'claimed'
    JOIN user_to_user_roles uur ON uur.user_id = dcn.depositor_id
    JOIN user_roles ur ON ur.id = uur.user_role_id AND ur.name = 'ambassador'
    JOIN users u_amb ON u_amb.id = dcn.depositor_id
    WHERE pd.code = 'zar_cash_exchange_merchant'
      AND pe.state = 2
      AND pe.created_at >= '{since}'
      {amb_filter}
),
with_gaps AS (
    SELECT
        ambassador,
        enroll_day,
        EXTRACT(EPOCH FROM (
            enrolled_at
            - LAG(enrolled_at) OVER (
                PARTITION BY ambassador_id, enroll_day
                ORDER BY enrolled_at
            )
        )) / 60.0                                                  AS mins_since_prev
    FROM pe_ambassadors
)
SELECT
    ambassador,
    enroll_day,
    COUNT(*) + 1                                                   AS enrollments_that_day,
    ROUND(AVG(mins_since_prev)::numeric, 1)                        AS avg_gap_min,
    ROUND(STDDEV(mins_since_prev)::numeric, 1)                     AS stddev_gap_min,
    ROUND(
        (STDDEV(mins_since_prev) / NULLIF(AVG(mins_since_prev), 0))::numeric, 3
    )                                                              AS cv_gap,
    ROUND(MIN(mins_since_prev)::numeric, 1)                        AS min_gap_min,
    ROUND(MAX(mins_since_prev)::numeric, 1)                        AS max_gap_min
FROM with_gaps
WHERE mins_since_prev IS NOT NULL
GROUP BY ambassador, enroll_day
HAVING COUNT(*) >= 3
ORDER BY cv_gap ASC NULLS LAST, COUNT(*) DESC
"""


def off_hours_enrollment_query(since='2026-02-01'):
    """PA7-F — Off-hours PE enrollment fraction per ambassador.

    Legitimate Karachi field work runs ~9am–7pm PKT. Enrollments outside
    this window (before 09:00 or at/after 19:00 PKT) signal desk-based
    batch submission rather than real field activity.

    Metric: pct_off_hours = fraction of each ambassador's PE enrollments
    outside the 9am–7pm PKT business window.

    Flag rule: >30% off-hours with ≥5 total enrollments = strong signal.

    Sources: FIELD_FRAUD researcher (fraudsters batch at night when
    supervisors are offline), Finextra onboarding fraud 2025.
    """
    return f"""
WITH pe_hours AS (
    SELECT
        u_amb.username                                             AS ambassador,
        pe.user_id                                                 AS merchant_id,
        (pe.created_at + INTERVAL '5 hours')                      AS enrolled_pkt,
        EXTRACT(HOUR FROM (pe.created_at + INTERVAL '5 hours'))   AS hour_pkt
    FROM product_enrollments pe
    JOIN product_definitions pd ON pd.id = pe.product_definition_id
    JOIN digital_cash_notes dcn ON dcn.claimant_id = pe.user_id
        AND dcn.status = 'claimed'
    JOIN user_to_user_roles uur ON uur.user_id = dcn.depositor_id
    JOIN user_roles ur ON ur.id = uur.user_role_id AND ur.name = 'ambassador'
    JOIN users u_amb ON u_amb.id = dcn.depositor_id
    WHERE pd.code = 'zar_cash_exchange_merchant'
      AND pe.state = 2
      AND pe.created_at >= '{since}'
)
SELECT
    ambassador,
    COUNT(*)                                                       AS total_enrollments,
    COUNT(*) FILTER (WHERE hour_pkt < 9 OR hour_pkt >= 19)        AS off_hours_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE hour_pkt < 9 OR hour_pkt >= 19)
        / COUNT(*), 0
    )                                                              AS pct_off_hours,
    COUNT(*) FILTER (WHERE hour_pkt BETWEEN 9 AND 18)             AS in_business_hours,
    COUNT(*) FILTER (WHERE hour_pkt >= 19)                        AS evening_night,
    COUNT(*) FILTER (WHERE hour_pkt < 9)                          AS early_morning,
    MIN(hour_pkt)                                                  AS earliest_hour,
    MAX(hour_pkt)                                                  AS latest_hour
FROM pe_hours
GROUP BY ambassador
HAVING COUNT(*) >= 3
ORDER BY pct_off_hours DESC NULLS LAST
"""


def leaf_node_analysis_query(phones=None, ambassador_id=FLAGGED_AMBASSADOR_ID):
    """PA7-H — Leaf node analysis: ghost merchants transact with no one but the ambassador.

    Real merchants, even dormant ones, occasionally receive P2P transfers from
    customers or suppliers. Ghost merchants are graph "leaf nodes" — their only
    connection is the enrolling ambassador's demo DCN. No other party has ever
    sent them money or received money from them.

    Checks ALL digital_cash_notes (any status) and ALL completed transactions
    for each suspect merchant, counting non-ambassador connections.

    node_type = 'LEAF_NODE' if non_ambassador_connections = 0.

    phones: list of E.164 phones. Defaults to 4 confirmed fakes.
    ambassador_id: whose DCNs count as the "expected" demo note.

    Sources: FIELD_FRAUD researcher, Cambridge Intelligence graph analytics.
    """
    if phones is None:
        phones = ['+923122388838', '+923113263959', '+923090336070', '+923192713284']
    phone_list = ", ".join(f"'{p}'" for p in phones)
    return f"""
WITH merchants AS (
    SELECT u.id AS user_id, u.phone_number
    FROM users u
    WHERE u.phone_number IN ({phone_list})
),
dcn_received AS (
    SELECT
        m.phone_number,
        m.user_id,
        'dcn_received'                                             AS activity_type,
        (dcn.depositor_id = '{ambassador_id}')                    AS is_ambassador_dcn,
        dcn.amount / 1e6                                           AS amount_usd,
        (dcn.created_at + INTERVAL '5 hours')                     AS event_pkt
    FROM merchants m
    JOIN digital_cash_notes dcn ON dcn.claimant_id = m.user_id
),
dcn_sent AS (
    SELECT
        m.phone_number,
        m.user_id,
        'dcn_sent'                                                 AS activity_type,
        FALSE                                                      AS is_ambassador_dcn,
        dcn.amount / 1e6                                           AS amount_usd,
        (dcn.created_at + INTERVAL '5 hours')                     AS event_pkt
    FROM merchants m
    JOIN digital_cash_notes dcn ON dcn.depositor_id = m.user_id
),
other_txns AS (
    SELECT
        m.phone_number,
        m.user_id,
        t.type                                                     AS activity_type,
        FALSE                                                      AS is_ambassador_dcn,
        t.amount / 1e6                                             AS amount_usd,
        (t.created_at + INTERVAL '5 hours')                       AS event_pkt
    FROM merchants m
    JOIN transactions t ON t.user_id = m.user_id
    WHERE t.status = 3
),
all_activity AS (
    SELECT * FROM dcn_received
    UNION ALL SELECT * FROM dcn_sent
    UNION ALL SELECT * FROM other_txns
)
SELECT
    m.phone_number,
    COUNT(a.event_pkt)                                             AS total_events,
    COUNT(*) FILTER (WHERE a.is_ambassador_dcn)                   AS ambassador_demo_dcns,
    COUNT(*) FILTER (
        WHERE NOT a.is_ambassador_dcn AND a.activity_type = 'dcn_received'
    )                                                              AS non_ambassador_dcns_received,
    COUNT(*) FILTER (WHERE a.activity_type = 'dcn_sent')          AS dcns_sent_by_merchant,
    COUNT(*) FILTER (
        WHERE a.activity_type NOT IN ('dcn_received', 'dcn_sent')
    )                                                              AS other_transactions,
    COUNT(*) FILTER (WHERE NOT a.is_ambassador_dcn)               AS non_ambassador_connections,
    CASE WHEN COUNT(*) FILTER (WHERE NOT a.is_ambassador_dcn) = 0
         THEN 'LEAF_NODE' ELSE 'connected' END                    AS node_type
FROM merchants m
LEFT JOIN all_activity a ON a.user_id = m.user_id
GROUP BY m.phone_number
ORDER BY non_ambassador_connections ASC
"""


def demo_note_amount_distribution_query(since='2026-02-01'):
    """PA7-I — Demo note amount distribution per ambassador (fleet-wide).

    Fraudsters send exactly $5.00 because that's the known demo amount.
    Real ambassadors may send variable amounts based on context ($3, $7, $10).
    A tight cluster at exactly 5,000,000 atomic USDC (= $5.00) with near-zero
    standard deviation is a formulaic, mechanized signal.

    Metric: pct_exactly_5 = fraction of demo DCNs at exactly $5.
    Flag: 100% pct_exactly_5 + stddev ≈ 0 = no creative variation.

    Only considers claimed DCNs sent by ambassadors (demo context).

    Sources: VARInsights incentive fraud research (WEB_RESEARCH).
    """
    return f"""
SELECT
    u_amb.username                                                 AS ambassador,
    COUNT(*)                                                       AS total_dcns,
    ROUND(MIN(dcn.amount / 1e6)::numeric, 3)                      AS min_usd,
    ROUND(MAX(dcn.amount / 1e6)::numeric, 3)                      AS max_usd,
    ROUND(AVG(dcn.amount / 1e6)::numeric, 4)                      AS avg_usd,
    ROUND(STDDEV(dcn.amount / 1e6)::numeric, 6)                   AS stddev_usd,
    COUNT(*) FILTER (WHERE dcn.amount = 5000000)                  AS exactly_5_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE dcn.amount = 5000000) / COUNT(*), 0
    )                                                              AS pct_exactly_5
FROM digital_cash_notes dcn
JOIN user_to_user_roles uur ON uur.user_id = dcn.depositor_id
JOIN user_roles ur ON ur.id = uur.user_role_id AND ur.name = 'ambassador'
JOIN users u_amb ON u_amb.id = dcn.depositor_id
WHERE dcn.status = 'claimed'
  AND dcn.claimed_at IS NOT NULL
  AND (dcn.created_at + INTERVAL '5 hours')::date >= '{since}'
GROUP BY u_amb.username
HAVING COUNT(*) >= 3
ORDER BY stddev_usd ASC NULLS LAST
"""
