"""
SQL queries for EXP-009 Directed Day — Atlas conventions.

Style: lowercase keywords, CTEs over subqueries, 4-space indent,
short table aliases (no AS), positional group by, PKT offset +5h.

Three query groups:
  1. Target generation — who to visit (onboarding + reactivation)
  2. Outcome tracking — did the visit work?
  3. Pool sizing — overall experiment health metrics
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.sql import EXCLUDED_IDS_SQL, merchants_cte


# ══════════════════════════════════════════════════════════════════════
# 1. TARGET GENERATION
# ══════════════════════════════════════════════════════════════════════

def reactivation_targets_query(city: str = "Karachi", inactive_days: int = 14) -> str:
    """Merchants with no ZCE (as fulfiller) and no CN (as depositor)
    in the last N days. These are reactivation visit targets.

    Output: merchant_id, business_name, lat, lng, phone, onboarding_date,
            last_activity_date, days_since_last_activity, lifetime_tx_count
    """
    return f"""
    with {merchants_cte(city=city)},

    -- Last ZCE activity per merchant (as fulfiller)
    last_zce as (
        select zce.fulfiller_id as merchant_id,
               max(zce.completed_at) as last_zce_at
        from zar_cash_exchange_orders zce
        where zce.status = 'completed'
          and zce.fulfiller_id in (select merchant_id from merchants)
        group by 1
    ),

    -- Last CN activity per merchant (as depositor)
    last_cn as (
        select dcn.depositor_id as merchant_id,
               max(dcn.claimed_at) as last_cn_at
        from digital_cash_notes dcn
        where dcn.status = 'claimed'
          and dcn.depositor_id in (select merchant_id from merchants)
        group by 1
    ),

    -- Last CashExchange activity per merchant
    last_ce as (
        select t.user_id as merchant_id,
               max(t.posted_at) as last_ce_at
        from transactions t
        where t.type = 'Transaction::CashExchange'
          and t.status = 3
          and t.metadata->>'role' = 'merchant'
          and coalesce(t.metadata->>'cancelled', 'false') != 'true'
          and t.user_id in (select merchant_id from merchants)
        group by 1
    ),

    -- Combined last activity
    last_activity as (
        select m.merchant_id,
               greatest(lz.last_zce_at, lc.last_cn_at, lce.last_ce_at) as last_activity_at
        from merchants m
        left join last_zce lz on lz.merchant_id = m.merchant_id
        left join last_cn lc on lc.merchant_id = m.merchant_id
        left join last_ce lce on lce.merchant_id = m.merchant_id
    ),

    -- Lifetime transaction counts
    lifetime_zce as (
        select zce.fulfiller_id as merchant_id,
               count(*) as zce_count
        from zar_cash_exchange_orders zce
        where zce.status = 'completed'
          and zce.fulfiller_id in (select merchant_id from merchants)
        group by 1
    ),
    lifetime_cn as (
        select dcn.depositor_id as merchant_id,
               count(*) as cn_count
        from digital_cash_notes dcn
        where dcn.status = 'claimed'
          and dcn.depositor_id in (select merchant_id from merchants)
        group by 1
    ),
    lifetime_ce as (
        select t.user_id as merchant_id,
               count(*) as ce_count
        from transactions t
        where t.type = 'Transaction::CashExchange'
          and t.status = 3
          and t.metadata->>'role' = 'merchant'
          and coalesce(t.metadata->>'cancelled', 'false') != 'true'
          and t.user_id in (select merchant_id from merchants)
        group by 1
    )

    select m.merchant_id::text,
           m.business_name,
           m.latitude,
           m.longitude,
           m.phone_number,
           m.onboarding_date::text,
           case when la.last_activity_at is not null
                then (la.last_activity_at + interval '5' hour)::date::text
                else null end as last_activity_date,
           case when la.last_activity_at is not null
                then extract(day from now() - la.last_activity_at)::int
                else null end as days_since_last_activity,
           coalesce(ltz.zce_count, 0) + coalesce(ltc.cn_count, 0) + coalesce(ltce.ce_count, 0) as lifetime_tx_count
    from merchants m
    inner join last_activity la on la.merchant_id = m.merchant_id
    left join lifetime_zce ltz on ltz.merchant_id = m.merchant_id
    left join lifetime_cn ltc on ltc.merchant_id = m.merchant_id
    left join lifetime_ce ltce on ltce.merchant_id = m.merchant_id
    where la.last_activity_at is null
       or la.last_activity_at < now() - interval '{inactive_days}' day
    order by la.last_activity_at asc nulls first
    """


def onboarding_status_check_query(phone_numbers: list[str]) -> str:
    """Check if visit-sheet merchants have since onboarded.

    Takes a list of phone numbers from the visit sheet and checks
    merchant_onboarding_submissions. Used to filter out merchants
    who onboarded after their demo visit.

    Output: phone_number, is_onboarded, onboarding_date
    """
    phones_sql = ", ".join(f"'{p}'" for p in phone_numbers)
    return f"""
    select u.phone_number,
           case when mos.id is not null or pe_check.user_id is not null then true else false end as is_onboarded,
           coalesce(
               (mos.created_at + interval '5' hour)::date::text,
               (pe_check.created_at + interval '5' hour)::date::text
           ) as onboarding_date
    from users u
    left join merchant_onboarding_submissions mos
        on mos.phone_number = u.phone_number
        and mos.status in ('active', 'pending')
    left join (
        select pe.user_id, pe.created_at
        from product_enrollments pe
        inner join product_definitions pd on pd.id = pe.product_definition_id
        where pd.code = 'zar_cash_exchange_merchant' and pe.state = 2
    ) pe_check on pe_check.user_id = u.id
    where u.phone_number in ({phones_sql})
    """


# ══════════════════════════════════════════════════════════════════════
# 2. OUTCOME TRACKING
# ══════════════════════════════════════════════════════════════════════

def onboarding_outcome_query(phone_numbers: list[str], visit_date: str) -> str:
    """Check if directed onboarding visits resulted in actual onboardings.

    Looks for merchant_onboarding_submissions created within 48h of
    the visit date for the given phone numbers.

    Output: phone_number, onboarded, onboarding_date, hours_after_visit
    """
    phones_sql = ", ".join(f"'{p}'" for p in phone_numbers)
    return f"""
    select u.phone_number,
           case when mos.id is not null or pe_check.user_id is not null then true else false end as onboarded,
           coalesce(
               (mos.created_at + interval '5' hour)::date::text,
               (pe_check.created_at + interval '5' hour)::date::text
           ) as onboarding_date,
           round(extract(epoch from (
               coalesce(mos.created_at, pe_check.created_at) - '{visit_date}'::timestamp
           )) / 3600.0, 1) as hours_after_visit
    from users u
    left join merchant_onboarding_submissions mos
        on mos.phone_number = u.phone_number
        and mos.status in ('active', 'pending')
        and (mos.created_at + interval '5' hour)::date >= '{visit_date}'::date
        and (mos.created_at + interval '5' hour)::date <= '{visit_date}'::date + interval '2' day
    left join (
        select pe.user_id, pe.created_at
        from product_enrollments pe
        inner join product_definitions pd on pd.id = pe.product_definition_id
        where pd.code = 'zar_cash_exchange_merchant' and pe.state = 2
          and (pe.created_at + interval '5' hour)::date >= '{visit_date}'::date
          and (pe.created_at + interval '5' hour)::date <= '{visit_date}'::date + interval '2' day
    ) pe_check on pe_check.user_id = u.id
    where u.phone_number in ({phones_sql})
    """


def reactivation_outcome_query(merchant_ids: list[str], visit_date: str) -> str:
    """Check if directed reactivation visits resulted in merchant activity.

    Looks for ZCE (as fulfiller) or CN (as depositor) within 7 days
    of the visit date.

    Output: merchant_id, reactivated, first_activity_type,
            first_activity_date, hours_after_visit
    """
    ids_sql = ", ".join(f"'{mid}'" for mid in merchant_ids)
    return f"""
    with target_merchants as (
        select unnest(array[{ids_sql}]::uuid[]) as merchant_id
    ),

    post_visit_zce as (
        select zce.fulfiller_id as merchant_id,
               min(zce.completed_at) as first_at,
               'zce' as activity_type
        from zar_cash_exchange_orders zce
        where zce.status = 'completed'
          and zce.fulfiller_id in (select merchant_id from target_merchants)
          and zce.completed_at >= '{visit_date}'::timestamp - interval '5' hour
          and zce.completed_at < '{visit_date}'::timestamp - interval '5' hour + interval '7' day
        group by 1
    ),

    post_visit_cn as (
        select dcn.depositor_id as merchant_id,
               min(dcn.claimed_at) as first_at,
               'cash_note' as activity_type
        from digital_cash_notes dcn
        where dcn.status = 'claimed'
          and dcn.depositor_id in (select merchant_id from target_merchants)
          and dcn.claimed_at >= '{visit_date}'::timestamp - interval '5' hour
          and dcn.claimed_at < '{visit_date}'::timestamp - interval '5' hour + interval '7' day
        group by 1
    ),

    post_visit_ce as (
        select t.user_id as merchant_id,
               min(t.posted_at) as first_at,
               'cash_exchange' as activity_type
        from transactions t
        where t.type = 'Transaction::CashExchange'
          and t.status = 3
          and t.metadata->>'role' = 'merchant'
          and coalesce(t.metadata->>'cancelled', 'false') != 'true'
          and t.user_id in (select merchant_id from target_merchants)
          and t.posted_at >= '{visit_date}'::timestamp - interval '5' hour
          and t.posted_at < '{visit_date}'::timestamp - interval '5' hour + interval '7' day
        group by 1
    ),

    all_activity as (
        select * from post_visit_zce
        union all
        select * from post_visit_cn
        union all
        select * from post_visit_ce
    ),

    earliest as (
        select merchant_id, first_at, activity_type,
               row_number() over (partition by merchant_id order by first_at) as rn
        from all_activity
    )

    select tm.merchant_id::text,
           case when e.merchant_id is not null then true else false end as reactivated,
           e.activity_type as first_activity_type,
           case when e.first_at is not null
                then (e.first_at + interval '5' hour)::date::text
                else null end as first_activity_date,
           case when e.first_at is not null
                then round(extract(epoch from (
                    e.first_at - ('{visit_date}'::timestamp - interval '5' hour)
                )) / 3600.0, 1)
                else null end as hours_after_visit
    from target_merchants tm
    left join earliest e on e.merchant_id = tm.merchant_id and e.rn = 1
    order by tm.merchant_id
    """


# ══════════════════════════════════════════════════════════════════════
# 3. POOL SIZING & HEALTH
# ══════════════════════════════════════════════════════════════════════

def pool_health_query(city: str = "Karachi", inactive_days: int = 14) -> str:
    """Overall experiment health: pool sizes, active vs inactive breakdown.

    Output: total_merchants, active_14d, inactive_14d, inactive_with_geo
    """
    return f"""
    with {merchants_cte(city=city)},

    recent_zce as (
        select distinct zce.fulfiller_id as merchant_id
        from zar_cash_exchange_orders zce
        where zce.status = 'completed'
          and zce.completed_at >= now() - interval '{inactive_days}' day
    ),
    recent_cn as (
        select distinct dcn.depositor_id as merchant_id
        from digital_cash_notes dcn
        where dcn.status = 'claimed'
          and dcn.claimed_at >= now() - interval '{inactive_days}' day
    ),
    recent_ce as (
        select distinct t.user_id as merchant_id
        from transactions t
        where t.type = 'Transaction::CashExchange'
          and t.status = 3
          and t.metadata->>'role' = 'merchant'
          and coalesce(t.metadata->>'cancelled', 'false') != 'true'
          and t.posted_at >= now() - interval '{inactive_days}' day
    ),
    active_merchants as (
        select merchant_id from recent_zce
        union
        select merchant_id from recent_cn
        union
        select merchant_id from recent_ce
    )

    select count(*) as total_merchants,
           count(*) filter (where act.merchant_id is not null) as active_14d,
           count(*) filter (where act.merchant_id is null) as inactive_14d,
           count(*) filter (
               where act.merchant_id is null
               and m.latitude is not null
               and m.longitude is not null
           ) as inactive_with_geo
    from merchants m
    left join active_merchants act on act.merchant_id = m.merchant_id
    """
