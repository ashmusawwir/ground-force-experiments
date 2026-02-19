"""SQL queries for DB-verified demo and onboarding status."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.sql import EXCLUDED_IDS_SQL, ambassadors_cte


def demo_onboarding_status_query() -> str:
    """Phone numbers that got a demo or onboarded since Feb 10.

    Demo check: sum of digital_cash_notes amounts from ambassadors to
    merchant must be >= 5,000,000 (i.e. $5 Golden Flow amount).
    All note recipients are included so DB verdict overrides sheet
    even for phones below the threshold.

    Onboarding check: MOS (phone_number, status active/pending) UNION
    PE (user_id -> users.phone_number, state = 2, merchant code).

    Output: phone_number, got_demo (bool), is_onboarded (bool)
    """
    return f"""
    with {ambassadors_cte()},
    note_recipients as (
        select u.phone_number, sum(dcn.amount) as total_amount
        from digital_cash_notes dcn
        inner join ambassadors a on a.ambassador_id = dcn.depositor_id
        inner join users u on u.id = dcn.claimant_id
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and (dcn.claimed_at + interval '5' hour)::date >= '2026-02-10'
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
        group by u.phone_number
    ),
    onboarded as (
        select distinct u.phone_number
        from merchant_onboarding_submissions mos
        inner join users u on u.phone_number = mos.phone_number
        where mos.status in ('active', 'pending')
          and (mos.created_at + interval '5' hour)::date >= '2026-02-10'
          and u.id not in ({EXCLUDED_IDS_SQL})
        union
        select distinct u.phone_number
        from product_enrollments pe
        inner join product_definitions pd on pd.id = pe.product_definition_id
        inner join users u on u.id = pe.user_id
        where pd.code = 'zar_cash_exchange_merchant'
          and pe.state = 2
          and (pe.created_at + interval '5' hour)::date >= '2026-02-10'
          and pe.user_id not in ({EXCLUDED_IDS_SQL})
    ),
    all_phones as (
        select phone_number from note_recipients
        union
        select phone_number from onboarded
    )
    select ap.phone_number,
           case when coalesce(nr.total_amount, 0) >= 5000000
                then true else false end as got_demo,
           case when o.phone_number is not null
                then true else false end as is_onboarded
    from all_phones ap
    left join note_recipients nr on nr.phone_number = ap.phone_number
    left join onboarded o on o.phone_number = ap.phone_number
    """
