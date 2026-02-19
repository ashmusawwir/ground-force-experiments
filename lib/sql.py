"""
Shared SQL building blocks for all experiments — Atlas conventions.

Style: lowercase keywords, CTEs over subqueries, 4-space indent,
short table aliases (no AS), positional group by, PKT offset +5h.

Usage in experiment queries.py:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from lib.sql import EXCLUDED_IDS_SQL, ambassadors_cte, merchants_cte
"""

from __future__ import annotations


# ── Exclusion lists ─────────────────────────────────────────────────

EXCLUDED_IDS = [
    '57d456f2-84f7-4db5-b5b8-4f494f29c9dc', '83845f51-170d-44b4-907b-68ba7e3a87d0',
    'bf1de49f-179a-400f-b023-2e73b57a59d9', 'aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
    'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec', 'f8780ccb-3d67-46e5-baa8-0811c64c730d',
    '84c74165-5eb6-4e4f-8b23-06892c09bdbc', '110228ec-0e17-482e-a692-3a34bdb3ab65',
    '9520d1e5-a92e-49d8-9a9e-6747523e0ed7', 'f32dd3b4-cad1-487b-8c87-e4924117c050',
    '5fd86e56-6c6d-426f-818e-f85898ec8dbf', '274bff97-2c1b-4410-a79d-dd81f33f5c15',
    '1b397809-6185-4273-b098-7d86cc821bc4', '44e72414-f6bc-4975-83fa-3046e28e9a94',
    'a464fe4a-ed62-41ca-87f4-4ab48d3c4058', '0eb006a5-53a8-41c2-9cca-6c06dc1c2549',
    '0aac7e5e-ac3a-49a3-b588-6fed46ca6ade', '0bc7e11b-5741-44b0-9c70-16fb5a58c2ee',
    '958a4910-a20f-4a06-81d6-d458dcc3bf57',  # Rick's guitar shop
]
EXCLUDED_IDS_SQL = ", ".join(f"'{uid}'" for uid in EXCLUDED_IDS)

# Transaction-specific exclusion list for cohort analysis (12 IDs).
# Differs from EXCLUDED_IDS: includes a9519a82 (Muhammad Zahid), omits
# 9520d1e5, f32dd3b4, 1b397809, a464fe4a, 0eb006a5, 0aac7e5e, 0bc7e11b, 958a4910.
COHORT_TXN_EXCLUDED_IDS = [
    '57d456f2-84f7-4db5-b5b8-4f494f29c9dc', '83845f51-170d-44b4-907b-68ba7e3a87d0',
    'bf1de49f-179a-400f-b023-2e73b57a59d9', 'aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
    'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec', 'f8780ccb-3d67-46e5-baa8-0811c64c730d',
    '84c74165-5eb6-4e4f-8b23-06892c09bdbc', '110228ec-0e17-482e-a692-3a34bdb3ab65',
    'a9519a82-c510-4b5b-a24b-ecec3f68de23', '44e72414-f6bc-4975-83fa-3046e28e9a94',
    '274bff97-2c1b-4410-a79d-dd81f33f5c15', '5fd86e56-6c6d-426f-818e-f85898ec8dbf',
]
COHORT_TXN_EXCLUDED_IDS_SQL = ", ".join(f"'{uid}'" for uid in COHORT_TXN_EXCLUDED_IDS)


# ── CTE generators ─────────────────────────────────────────────────

def ambassadors_cte() -> str:
    """Users with the ambassador role, excluding test accounts.

    Returns CTE named ``ambassadors`` with column: ``ambassador_id``.
    """
    return f"""ambassadors as (
        select distinct uur.user_id as ambassador_id
        from user_to_user_roles uur
        inner join user_roles ur on ur.id = uur.user_role_id
        where ur.name = 'ambassador'
          and uur.user_id not in ({EXCLUDED_IDS_SQL})
    )"""


def merchants_cte(
    city: str | None = None,
    since: str | None = None,
) -> str:
    """Onboarded merchants via MOS + PE union (SHIP-2069, Dec 13).

    Returns CTEs named ``mos_merchants``, ``pe_merchants``, ``merchants``.
    When *since* is provided, also returns ``qualifying`` (date-filtered subset).

    Columns (superset — callers select only what they need):
        merchant_id, business_name, city, latitude, longitude, status,
        phone_number, onboarding_date, onboarder_username, onboarder_name

    Args:
        city:  Filter to this city (case-insensitive). None = all cities.
               Note: PE merchants have no city field — city filter returns
               only MOS merchants (PE rows filtered out, known limitation).
        since: Only merchants onboarded on/after this date (YYYY-MM-DD).
               Adds a ``qualifying`` CTE; downstream queries should reference
               ``qualifying`` instead of ``merchants`` when using this param.
    """
    city_mos = f"\n          and lower(coalesce(mos.city, '')) = '{city.lower()}'" if city else ""
    city_pe = f"\n          and lower(coalesce(null::text, '')) = '{city.lower()}'" if city else ""

    qualifying = ""
    if since:
        qualifying = f"""), qualifying as (
        select * from merchants
        where onboarding_date >= '{since}'"""

    return f"""mos_merchants as (
        select distinct on (u.id)
               u.id as merchant_id, mos.business_name,
               mos.city, mos.latitude, mos.longitude, mos.status,
               u.phone_number,
               (mos.created_at + interval '5' hour)::date as onboarding_date,
               u_onb.username as onboarder_username,
               coalesce(nullif(trim(concat(coalesce(u_onb.first_name,''),' ',coalesce(u_onb.last_name,''))), ''), 'Unknown') as onboarder_name
        from merchant_onboarding_submissions mos
        inner join users u on u.phone_number = mos.phone_number
        left join users u_onb on u_onb.id = mos.onboarder_id
        where mos.status in ('active', 'pending')
          and lower(mos.business_name) not like '%test%'
          and u.id not in ({EXCLUDED_IDS_SQL}){city_mos}
        order by u.id, mos.created_at desc
    ), pe_merchants as (
        select pe.user_id as merchant_id,
               null::text as business_name,
               null::text as city,
               null::float8 as latitude,
               null::float8 as longitude,
               'pe_enrolled' as status,
               u.phone_number,
               (pe.created_at + interval '5' hour)::date as onboarding_date,
               null::text as onboarder_username,
               'Unknown' as onboarder_name
        from product_enrollments pe
        inner join product_definitions pd on pd.id = pe.product_definition_id
        inner join users u on u.id = pe.user_id
        where pd.code = 'zar_cash_exchange_merchant'
          and pe.state = 2
          and pe.user_id not in ({EXCLUDED_IDS_SQL})
          and pe.user_id not in (select merchant_id from mos_merchants){city_pe}
    ), merchants as (
        select * from mos_merchants
        union all
        select * from pe_merchants
    {qualifying})"""


def is_onboarded_check(user_id_col: str, phone_col: str) -> str:
    """Reusable boolean expression: is this user an onboarded merchant?

    Checks both MOS (phone match) and PE (user_id match). Returns a SQL
    boolean expression (PostgreSQL ``exists`` returns bool).

    Usage in SELECT:
        ``{is_onboarded_check('u.id', 'u.phone_number')} as is_onboarded``
    Usage in WHERE:
        ``where {is_onboarded_check('u.id', 'u.phone_number')}``

    Args:
        user_id_col: Column reference for user ID (e.g. ``rb.recipient_id``)
        phone_col:   Column reference for phone number (e.g. ``u.phone_number``)
    """
    return f"""(exists (
            select 1 from merchant_onboarding_submissions mos
            where mos.phone_number = {phone_col}
              and mos.status in ('active', 'pending')
        ) or exists (
            select 1 from product_enrollments pe
            inner join product_definitions pd on pd.id = pe.product_definition_id
            where pe.user_id = {user_id_col}
              and pd.code = 'zar_cash_exchange_merchant'
              and pe.state = 2
        ))"""


def demo_dollars_cte() -> str:
    """Cash notes from ambassadors to same-day-created recipients (Feb 1+).

    Requires ``ambassadors`` CTE already in scope. Does NOT filter on amount
    so the note distribution card can show the $5-single vs split breakdown.

    Returns CTE named ``demo_dollars`` with columns:
        note_id, ambassador_id, recipient_id, amount_usd, claimed_date, claimed_at
    """
    return """demo_dollars as (
        select dcn.id as note_id,
               dcn.depositor_id as ambassador_id,
               dcn.claimant_id as recipient_id,
               dcn.amount / 1e6 as amount_usd,
               (dcn.claimed_at + interval '5' hour)::date as claimed_date,
               dcn.claimed_at
        from digital_cash_notes dcn
        inner join ambassadors a on a.ambassador_id = dcn.depositor_id
        inner join users u on u.id = dcn.claimant_id
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and (dcn.claimed_at + interval '5' hour)::date >= '2026-02-01'
          and (u.created_at + interval '5' hour)::date = (dcn.claimed_at + interval '5' hour)::date
          and dcn.claimant_id not in (select ambassador_id from ambassadors)
    )"""
