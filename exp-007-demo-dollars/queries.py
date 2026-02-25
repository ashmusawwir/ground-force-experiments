"""SQL queries for DB-verified demo and onboarding status with dates."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.sql import EXCLUDED_IDS_SQL, ambassadors_cte


def retargeting_status_query():
    """Per-phone demo and onboarding status with dates for retargeting analysis.

    Demo check: any digital_cash_note from an ambassador (amount > 0).
    Returns first_demo_date for timeline correlation with sheet visits.

    Onboarding check: MOS (active/pending) UNION PE (state=2, merchant code).
    No date filter — checks all-time records.

    Output: phone_number, got_demo, first_demo_date, is_onboarded, onboarding_date
    """
    return f"""
    with {ambassadors_cte()},
    demo_notes as (
        select u.phone_number,
               min((dcn.claimed_at + interval '5' hour)::date) as first_demo_date,
               sum(dcn.amount) as total_amount
        from digital_cash_notes dcn
        inner join ambassadors a on a.ambassador_id = dcn.depositor_id
        inner join users u on u.id = dcn.claimant_id
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
        group by u.phone_number
    ),
    onboarded as (
        select phone_number, min(onboarding_date) as onboarding_date
        from (
            select u.phone_number,
                   min((mos.created_at + interval '5' hour)::date) as onboarding_date
            from merchant_onboarding_submissions mos
            inner join users u on u.phone_number = mos.phone_number
            where mos.status in ('active', 'pending')
              and u.id not in ({EXCLUDED_IDS_SQL})
            group by u.phone_number

            union all

            select u.phone_number,
                   min((pe.created_at + interval '5' hour)::date) as onboarding_date
            from product_enrollments pe
            inner join product_definitions pd on pd.id = pe.product_definition_id
            inner join users u on u.id = pe.user_id
            where pd.code = 'zar_cash_exchange_merchant'
              and pe.state = 2
              and pe.user_id not in ({EXCLUDED_IDS_SQL})
            group by u.phone_number
        ) x
        group by phone_number
    ),
    all_phones as (
        select phone_number from demo_notes
        union
        select phone_number from onboarded
    )
    select ap.phone_number,
           coalesce(dn.total_amount, 0) > 0 as got_demo,
           dn.first_demo_date,
           o.phone_number is not null as is_onboarded,
           o.onboarding_date
    from all_phones ap
    left join demo_notes dn on dn.phone_number = ap.phone_number
    left join onboarded o on o.phone_number = ap.phone_number
    """
