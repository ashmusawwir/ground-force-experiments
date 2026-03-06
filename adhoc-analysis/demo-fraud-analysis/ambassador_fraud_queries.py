"""
SQL queries for ambassador fraud investigation reports.
Single source of truth — run via Rube MCP (METABASE_POST_API_DATASET, database=1).

All queries use PKT offset (+5h), exclude test accounts (EXCLUDED_IDS),
and exclude supervisors Qasim Fazal / Turab Abbas by name.

Usage:
    from ambassador_fraud_queries import discovery_query, demo_overview_query, ...
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.sql import EXCLUDED_IDS_SQL

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
    '958a4910-a20f-4a06-81d6-d458dcc3bf57',
]

def _ids_array(ids):
    """Format a list of UUIDs as a PostgreSQL ARRAY literal."""
    return "ARRAY['" + "','".join(ids) + "']::uuid[]"


def discovery_query(start_date='2026-02-26', end_date='2026-03-05'):
    """Find all active ambassadors (sent demos in date range), excluding Qasim/Turab."""
    return f"""
with amb as (
    select u.id, u.phone_number, u.username, u.first_name, u.last_name,
           min((utur.created_at + interval '5' hour)::date) as role_assigned_date
    from users u
    join user_to_user_roles utur on utur.user_id = u.id
    join user_roles ur on ur.id = utur.user_role_id and ur.name = 'ambassador'
    where u.id not in ({EXCLUDED_IDS_SQL})
      and lower(coalesce(u.first_name,'') || ' ' || coalesce(u.last_name,'')) not like '%qasim%'
      and lower(coalesce(u.first_name,'') || ' ' || coalesce(u.last_name,'')) not like '%turab%'
      and lower(coalesce(u.username,'')) not like '%qasim%'
      and lower(coalesce(u.username,'')) not like '%turab%'
    group by u.id, u.phone_number, u.username, u.first_name, u.last_name
),
active as (
    select distinct a.id
    from amb a
    join digital_cash_notes dcn on dcn.depositor_id = a.id and dcn.status = 'claimed'
    where (dcn.created_at + interval '5' hour)::date >= '{start_date}'
      and (dcn.created_at + interval '5' hour)::date <= '{end_date}'
)
select a.id, a.phone_number, a.username, a.first_name, a.last_name, a.role_assigned_date
from amb a join active ac on ac.id = a.id
order by a.phone_number
"""


def demo_overview_query(ids):
    """Q-A: All-time demo stats per ambassador including account_created."""
    arr = _ids_array(ids)
    return f"""
with daily_max as (
    select depositor_id, max(cnt) as max_per_day
    from (
        select depositor_id, (created_at + interval '5' hour)::date, count(*) as cnt
        from digital_cash_notes
        where depositor_id = any({arr}) and status = 'claimed'
        group by depositor_id, (created_at + interval '5' hour)::date
    ) x
    group by depositor_id
)
select dcn.depositor_id as ambassador_id,
       (u.created_at + interval '5' hour)::date as account_created,
       count(*) as total_demos,
       count(*) * 5.0 as total_usd,
       min((dcn.created_at + interval '5' hour)::date) as first_demo_date,
       max((dcn.created_at + interval '5' hour)::date) as last_demo_date,
       dm.max_per_day,
       count(distinct (dcn.created_at + interval '5' hour)::date) as active_days,
       count(distinct dcn.claimant_id) as total_recipients
from digital_cash_notes dcn
join users u on u.id = dcn.depositor_id
join daily_max dm on dm.depositor_id = dcn.depositor_id
where dcn.depositor_id = any({arr}) and dcn.status = 'claimed'
group by dcn.depositor_id, u.created_at, dm.max_per_day
"""


def demo_timeline_query(ids):
    """Q-B: Demo count per ambassador per day (all time)."""
    arr = _ids_array(ids)
    return f"""
select depositor_id as ambassador_id,
       (created_at + interval '5' hour)::date as demo_date,
       count(*) as demo_count
from digital_cash_notes
where depositor_id = any({arr}) and status = 'claimed'
group by depositor_id, (created_at + interval '5' hour)::date
order by depositor_id, demo_date desc
"""


def peer_comparison_query():
    """Q-C: All ambassadors ranked by total demo count (excluding Qasim/Turab/test accounts)."""
    return f"""
with all_amb as (
    select u.id, u.phone_number,
           count(dcn.id) as total_demos
    from users u
    join user_to_user_roles utur on utur.user_id = u.id
    join user_roles ur on ur.id = utur.user_role_id and ur.name = 'ambassador'
    left join digital_cash_notes dcn on dcn.depositor_id = u.id and dcn.status = 'claimed'
    where u.id not in ({EXCLUDED_IDS_SQL})
      and lower(coalesce(u.first_name,'') || ' ' || coalesce(u.last_name,'')) not like '%qasim%'
      and lower(coalesce(u.first_name,'') || ' ' || coalesce(u.last_name,'')) not like '%turab%'
    group by u.id, u.phone_number
)
select row_number() over (order by total_demos desc) as rank,
       id, phone_number, total_demos
from all_amb
order by total_demos desc
"""


def merchant_onboardings_query(ids):
    """Q-D: Recipient merchant onboardings (MOS + PE) per ambassador."""
    arr = _ids_array(ids)
    return f"""
with recipients as (
    select depositor_id as ambassador_id, claimant_id as user_id
    from digital_cash_notes
    where depositor_id = any({arr}) and status = 'claimed'
),
mos_ob as (
    select r.ambassador_id, u.phone_number,
           min((mos.created_at + interval '5' hour)::date) as onboarded_date, 'MOS' as pathway
    from recipients r
    join users u on u.id = r.user_id
    join merchant_onboarding_submissions mos on mos.phone_number = u.phone_number
    where mos.status in ('active','pending')
    group by r.ambassador_id, u.phone_number
),
pe_ob as (
    select r.ambassador_id, u.phone_number,
           min((pe.created_at + interval '5' hour)::date) as onboarded_date, 'PE' as pathway
    from recipients r
    join users u on u.id = r.user_id
    join product_enrollments pe on pe.user_id = r.user_id
    join product_definitions pd on pd.id = pe.product_definition_id
    where pd.code = 'zar_cash_exchange_merchant' and pe.state = 2
    group by r.ambassador_id, u.phone_number
)
select * from mos_ob union all select * from pe_ob
order by ambassador_id, onboarded_date
"""


def recipient_activity_query(ids):
    """Q-E: Post-demo transactions by recipients (excludes DCN type)."""
    arr = _ids_array(ids)
    return f"""
with recipients as (
    select depositor_id as ambassador_id, claimant_id as user_id,
           min(created_at) as demo_at
    from digital_cash_notes
    where depositor_id = any({arr}) and status = 'claimed'
    group by depositor_id, claimant_id
)
select r.ambassador_id, u.phone_number,
       t.type, t.amount / 1e6 as amount_usd,
       case when t.direction = 0 then 'Debit' else 'Credit' end as direction,
       (t.created_at + interval '5' hour)::date as txn_date
from recipients r
join users u on u.id = r.user_id
join transactions t on t.user_id = r.user_id
  and t.created_at > r.demo_at
  and t.status = 3
where t.type not in ('Transaction::DigitalCashNote')
order by r.ambassador_id, txn_date
"""


def card_self_spend_query(ids):
    """Q-F: Ambassador self-spend — CashExchange as customer + ZCE as initiator."""
    arr = _ids_array(ids)
    return f"""
select t.user_id as ambassador_id, t.type, t.amount / 1e6 as amount_usd,
       (t.created_at + interval '5' hour)::date as txn_date
from transactions t
where t.user_id = any({arr})
  and t.type = 'Transaction::CashExchange'
  and t.status = 3
  and coalesce(t.metadata->>'cancelled','false') != 'true'
  and t.metadata->>'role' = 'customer'
union all
select initiator_id, 'ZCE' as type, amount / 1e6,
       (created_at + interval '5' hour)::date
from zar_cash_exchange_orders
where initiator_id = any({arr}) and status = 'completed'
order by ambassador_id, txn_date
"""


def money_loop_query(ids):
    """Q-G: Recipients sending money back to ambassador (counterparty or BankTransfer recipient)."""
    arr = _ids_array(ids)
    return f"""
with recipients as (
    select depositor_id as ambassador_id, claimant_id as user_id
    from digital_cash_notes
    where depositor_id = any({arr}) and status = 'claimed'
)
select r.ambassador_id, u.phone_number as recipient_phone,
       t.amount / 1e6 as amount_usd,
       (t.created_at + interval '5' hour)::date as txn_date
from recipients r
join users u on u.id = r.user_id
join transactions t on t.user_id = r.user_id
  and t.status = 3
where t.metadata->>'counterparty_id' = r.ambassador_id::text
   or (t.type = 'Transaction::BankTransfer'
       and t.metadata->>'recipient_id' = r.ambassador_id::text)
order by r.ambassador_id, amount_usd desc
"""


def incoming_budget_query(ids):
    """Q-H: Who sent DCNs to each ambassador (budget sources)."""
    arr = _ids_array(ids)
    return f"""
select dcn.claimant_id as ambassador_id,
       coalesce(u.first_name,'') || ' ' || coalesce(u.last_name,'') as sender_name,
       u.phone_number as sender_phone,
       count(*) as txn_count,
       count(*) * 5 as total_usd
from digital_cash_notes dcn
join users u on u.id = dcn.depositor_id
where dcn.claimant_id = any({arr}) and dcn.status = 'claimed'
group by dcn.claimant_id, u.id, u.first_name, u.last_name, u.phone_number
order by ambassador_id, total_usd desc
"""
