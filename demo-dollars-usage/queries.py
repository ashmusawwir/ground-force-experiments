"""
SQL queries for demo dollars usage analysis — Atlas conventions.

Style: lowercase keywords, CTEs over subqueries, 4-space indent,
short table aliases (no AS), positional group by, PKT offset +5h.

These are the canonical queries for this experiment. run.py reads from
cache but these are here for direct fetching via Rube MCP.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.sql import EXCLUDED_IDS_SQL, ambassadors_cte, demo_dollars_cte, is_onboarded_check


# ── Query 1: Recipient Overview ──────────────────────────────────────

def recipient_overview_query() -> str:
    """Per-recipient row: recipient_id, is_onboarded, account_created_date, ambassador info."""
    return f"""
    with {ambassadors_cte()},
    {demo_dollars_cte()},

    recipient_base as (
        select dd.recipient_id,
               min(dd.ambassador_id::text)::uuid as first_ambassador_id,
               min(dd.claimed_date) as first_demo_date,
               sum(dd.amount_usd) as total_received,
               count(*) as notes_received
        from demo_dollars dd
        group by 1
    )

    select rb.recipient_id::text,
           rb.first_ambassador_id::text as ambassador_id,
           coalesce(nullif(trim(concat(coalesce(ua.first_name,''),' ',coalesce(ua.last_name,''))), ''), ua.username, 'Unknown') as ambassador_name,
           rb.first_demo_date::text as account_created_date,
           rb.total_received,
           rb.notes_received,
           {is_onboarded_check('rb.recipient_id', 'u.phone_number')} as is_onboarded,
           coalesce(mos.business_name, mos_mid.business_name) as business_name,
           u.phone_number as recipient_phone,
           coalesce(nullif(trim(concat(coalesce(u.first_name,''),' ',coalesce(u.last_name,''))), ''), u.username) as recipient_name,
           case when (u.email is not null and u.email != '')
                  or (u.phone_number is not null and u.phone_number != '')
                then true else false end as is_secured
    from recipient_base rb
    inner join users u on u.id = rb.recipient_id
    left join users ua on ua.id = rb.first_ambassador_id
    left join merchant_onboarding_submissions mos
        on mos.phone_number = u.phone_number
        and mos.status in ('active', 'pending')
    left join merchant_onboarding_submissions mos_mid
        on mos_mid.merchant_id = rb.recipient_id
        and mos.id is null
    order by rb.first_demo_date, rb.recipient_id
    """


# ── Query 2: Note Distribution ───────────────────────────────────────

def note_distribution_query() -> str:
    """Per-recipient aggregation: note_count, total_amount, first_note_date, pattern."""
    return f"""
    with {ambassadors_cte()},
    {demo_dollars_cte()},

    per_recipient as (
        select dd.recipient_id,
               count(*) as note_count,
               sum(dd.amount_usd) as total_amount,
               min(dd.claimed_date) as first_note_date,
               max(dd.amount_usd) as max_note,
               min(dd.amount_usd) as min_note
        from demo_dollars dd
        group by 1
    )

    select pr.recipient_id::text,
           pr.note_count,
           round(pr.total_amount::numeric, 2) as total_amount,
           pr.first_note_date::text,
           case
               when pr.note_count = 1 and round(pr.total_amount::numeric, 2) = 5.00 then 'single_5'
               when pr.note_count > 1 then 'multiple_notes'
               else 'other'
           end as pattern
    from per_recipient pr
    order by pr.first_note_date, pr.recipient_id
    """


# ── Query 3: Recipient Activity ──────────────────────────────────────

def recipient_activity_query() -> str:
    """Per-recipient post-demo activity with ambassador cycling split."""
    return f"""
    with {ambassadors_cte()},
    {demo_dollars_cte()},

    first_demo as (
        select dd.recipient_id,
               min(dd.claimed_at) as first_claimed_at,
               min(dd.ambassador_id::text)::uuid as first_ambassador_id
        from demo_dollars dd
        group by 1
    ),

    -- CN sends by recipient AFTER first demo receipt
    cn_sends_to_amb as (
        select fd.recipient_id,
               count(*) as cn_send_to_amb_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as cn_send_to_amb_volume
        from first_demo fd
        inner join digital_cash_notes dcn on dcn.depositor_id = fd.recipient_id
            and dcn.claimant_id = fd.first_ambassador_id
            and dcn.status = 'claimed'
            and dcn.created_at > fd.first_claimed_at
        group by 1
    ),

    cn_sends_to_others as (
        select fd.recipient_id,
               count(*) as cn_send_to_others_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as cn_send_to_others_volume
        from first_demo fd
        inner join digital_cash_notes dcn on dcn.depositor_id = fd.recipient_id
            and dcn.status = 'claimed'
            and dcn.created_at > fd.first_claimed_at
            and dcn.claimant_id not in (select ambassador_id from ambassadors)
        group by 1
    ),

    -- Card spend
    card_spend as (
        select fd.recipient_id,
               count(*) as card_count,
               round((sum(abs(t.amount)) / 1e6)::numeric, 2) as card_volume
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::CardSpend'
            and t.posted_at > fd.first_claimed_at
        group by 1
    ),

    -- Bank transfers
    bank_transfers as (
        select fd.recipient_id,
               count(*) as bt_count,
               round((sum(abs(t.amount)) / 1e6)::numeric, 2) as bt_volume
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::BankTransfer'
            and t.posted_at > fd.first_claimed_at
        group by 1
    ),

    -- ZCE orders
    zce_orders as (
        select fd.recipient_id,
               count(*) as zce_count,
               round((sum(zce.amount) / 1e6)::numeric, 2) as zce_volume
        from first_demo fd
        inner join zar_cash_exchange_orders zce on zce.initiator_id = fd.recipient_id
            and zce.status = 'completed'
            and zce.created_at > fd.first_claimed_at
        group by 1
    ),

    -- CashExchange orders (customer-side)
    ce_orders as (
        select fd.recipient_id,
               count(*) as ce_count,
               round((sum(t.amount) / 1e6)::numeric, 2) as ce_volume
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.type = 'Transaction::CashExchange'
            and t.status = 3
            and t.metadata->>'role' = 'customer'
            and coalesce(t.metadata->>'cancelled', 'false') != 'true'
            and t.posted_at > fd.first_claimed_at
        group by 1
    )

    select fd.recipient_id::text,
           coalesce(csa.cn_send_to_amb_count, 0) as cn_send_to_amb_count,
           coalesce(csa.cn_send_to_amb_volume, 0) as cn_send_to_amb_volume,
           coalesce(cso.cn_send_to_others_count, 0) as cn_send_to_others_count,
           coalesce(cso.cn_send_to_others_volume, 0) as cn_send_to_others_volume,
           coalesce(cs.card_count, 0) as card_count,
           coalesce(cs.card_volume, 0) as card_volume,
           coalesce(bt.bt_count, 0) as bt_count,
           coalesce(bt.bt_volume, 0) as bt_volume,
           coalesce(zce.zce_count, 0) as zce_count,
           coalesce(zce.zce_volume, 0) as zce_volume,
           coalesce(ce.ce_count, 0) as ce_count,
           coalesce(ce.ce_volume, 0) as ce_volume
    from first_demo fd
    left join cn_sends_to_amb csa on csa.recipient_id = fd.recipient_id
    left join cn_sends_to_others cso on cso.recipient_id = fd.recipient_id
    left join card_spend cs on cs.recipient_id = fd.recipient_id
    left join bank_transfers bt on bt.recipient_id = fd.recipient_id
    left join zce_orders zce on zce.recipient_id = fd.recipient_id
    left join ce_orders ce on ce.recipient_id = fd.recipient_id
    order by fd.recipient_id
    """


# ── Query 4: Ambassador Summary ──────────────────────────────────────

def ambassador_summary_query() -> str:
    """Per-ambassador: notes sent, unique recipients, onboarded count, conversion rate."""
    return f"""
    with {ambassadors_cte()},
    {demo_dollars_cte()},

    amb_stats as (
        select dd.ambassador_id,
               count(*) as notes_sent,
               count(distinct dd.recipient_id) as unique_recipients,
               sum(dd.amount_usd) as total_given
        from demo_dollars dd
        group by 1
    ),

    onboarded as (
        select dd.ambassador_id,
               count(distinct dd.recipient_id) as onboarded_count
        from demo_dollars dd
        inner join users u on u.id = dd.recipient_id
        where {is_onboarded_check('u.id', 'u.phone_number')}
        group by 1
    )

    select ast.ambassador_id::text,
           coalesce(nullif(trim(concat(coalesce(ua.first_name,''),' ',coalesce(ua.last_name,''))), ''), ua.username, 'Unknown') as ambassador_name,
           ast.notes_sent,
           ast.unique_recipients,
           round(ast.total_given::numeric, 2) as total_given,
           coalesce(onb.onboarded_count, 0) as onboarded_count,
           case when ast.unique_recipients > 0
                then round((coalesce(onb.onboarded_count, 0)::numeric / ast.unique_recipients) * 100, 1)
                else 0 end as conversion_rate
    from amb_stats ast
    inner join users ua on ua.id = ast.ambassador_id
    left join onboarded onb on onb.ambassador_id = ast.ambassador_id
    order by ast.unique_recipients desc
    """


# ── Query 5: Recipient Timing ─────────────────────────────────────

def recipient_timing_query() -> str:
    """Per-recipient: first qualifying activity timestamp + days/hours delta.

    Atlas Five Questions:
      Metric:  first qualifying activity timestamp per recipient
      Entity:  all demo dollar recipients
      Time:    post-demo-receipt, no upper bound
      Group:   per recipient_id
      Output:  demo_date, first_activity_date, first_activity_type,
               days_to_first_activity, hours_to_first_activity
    """
    return f"""
    with {ambassadors_cte()},
    {demo_dollars_cte()},

    first_demo as (
        select dd.recipient_id,
               min(dd.claimed_at) as first_claimed_at,
               min(dd.ambassador_id::text)::uuid as first_ambassador_id
        from demo_dollars dd
        group by 1
    ),

    -- Per-type first qualifying activity timestamps (excludes cycling)
    first_cn_send as (
        select fd.recipient_id,
               min(dcn.created_at) as first_ts,
               'cn_send' as activity_type
        from first_demo fd
        inner join digital_cash_notes dcn on dcn.depositor_id = fd.recipient_id
            and dcn.status = 'claimed'
            and dcn.created_at > fd.first_claimed_at
            and dcn.claimant_id not in (select ambassador_id from ambassadors)
        group by 1
    ),

    first_card as (
        select fd.recipient_id,
               min(t.posted_at) as first_ts,
               'card_spend' as activity_type
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::CardSpend'
            and t.posted_at > fd.first_claimed_at
        group by 1
    ),

    first_bt as (
        select fd.recipient_id,
               min(t.posted_at) as first_ts,
               'bank_transfer' as activity_type
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::BankTransfer'
            and t.posted_at > fd.first_claimed_at
        group by 1
    ),

    first_zce as (
        select fd.recipient_id,
               min(zce.created_at) as first_ts,
               'zce_order' as activity_type
        from first_demo fd
        inner join zar_cash_exchange_orders zce on zce.initiator_id = fd.recipient_id
            and zce.status = 'completed'
            and zce.created_at > fd.first_claimed_at
        group by 1
    ),

    first_ce as (
        select fd.recipient_id,
               min(t.posted_at) as first_ts,
               'cash_exchange' as activity_type
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.type = 'Transaction::CashExchange'
            and t.status = 3
            and t.metadata->>'role' = 'customer'
            and coalesce(t.metadata->>'cancelled', 'false') != 'true'
            and t.posted_at > fd.first_claimed_at
        group by 1
    ),

    -- Union all first timestamps, pick earliest per recipient
    all_firsts as (
        select recipient_id, first_ts, activity_type from first_cn_send
        union all
        select recipient_id, first_ts, activity_type from first_card
        union all
        select recipient_id, first_ts, activity_type from first_bt
        union all
        select recipient_id, first_ts, activity_type from first_zce
        union all
        select recipient_id, first_ts, activity_type from first_ce
    ),

    earliest as (
        select af.recipient_id, af.first_ts, af.activity_type,
               row_number() over (partition by af.recipient_id order by af.first_ts) as rn
        from all_firsts af
    )

    select fd.recipient_id::text,
           (fd.first_claimed_at + interval '5' hour)::date::text as demo_date,
           case when e.first_ts is not null
                then (e.first_ts + interval '5' hour)::date::text
                else null end as first_activity_date,
           e.activity_type as first_activity_type,
           case when e.first_ts is not null
                then round(extract(epoch from (e.first_ts - fd.first_claimed_at)) / 86400.0, 2)
                else null end as days_to_first_activity,
           case when e.first_ts is not null
                then round(extract(epoch from (e.first_ts - fd.first_claimed_at)) / 3600.0, 2)
                else null end as hours_to_first_activity
    from first_demo fd
    left join earliest e on e.recipient_id = fd.recipient_id and e.rn = 1
    order by fd.first_claimed_at, fd.recipient_id
    """


# ── Query 6: Demo Merchant Transactions (EXP-007) ───────────────────

def demo_merchant_transactions_query() -> str:
    """Per-recipient: 7-day post-demo transaction activity.

    Atlas Five Questions:
      Metric:  transaction count and volume by type per recipient
      Entity:  all demo dollar recipients
      Time:    7 days post-demo receipt
      Group:   per recipient_id, transaction type
      Output:  recipient_id, tx_type, tx_count, tx_volume, first_tx_at
    """
    return f"""
    with {ambassadors_cte()},
    {demo_dollars_cte()},

    first_demo as (
        select dd.recipient_id,
               min(dd.claimed_at) as first_claimed_at
        from demo_dollars dd
        group by 1
    ),

    -- Cash note sends (excluding cycling back to ambassador)
    cn_txns as (
        select fd.recipient_id,
               'cn_send' as tx_type,
               count(*) as tx_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as tx_volume,
               min(dcn.created_at) as first_tx_at
        from first_demo fd
        inner join digital_cash_notes dcn on dcn.depositor_id = fd.recipient_id
            and dcn.status = 'claimed'
            and dcn.created_at > fd.first_claimed_at
            and dcn.created_at <= fd.first_claimed_at + interval '7' day
            and dcn.claimant_id not in (select ambassador_id from ambassadors)
        group by 1
    ),

    -- Card spend
    card_txns as (
        select fd.recipient_id,
               'card_spend' as tx_type,
               count(*) as tx_count,
               round((sum(abs(t.amount)) / 1e6)::numeric, 2) as tx_volume,
               min(t.posted_at) as first_tx_at
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::CardSpend'
            and t.posted_at > fd.first_claimed_at
            and t.posted_at <= fd.first_claimed_at + interval '7' day
        group by 1
    ),

    -- Bank transfers
    bt_txns as (
        select fd.recipient_id,
               'bank_transfer' as tx_type,
               count(*) as tx_count,
               round((sum(abs(t.amount)) / 1e6)::numeric, 2) as tx_volume,
               min(t.posted_at) as first_tx_at
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::BankTransfer'
            and t.posted_at > fd.first_claimed_at
            and t.posted_at <= fd.first_claimed_at + interval '7' day
        group by 1
    ),

    -- ZCE orders
    zce_txns as (
        select fd.recipient_id,
               'zce_order' as tx_type,
               count(*) as tx_count,
               round((sum(zce.amount) / 1e6)::numeric, 2) as tx_volume,
               min(zce.created_at) as first_tx_at
        from first_demo fd
        inner join zar_cash_exchange_orders zce on zce.initiator_id = fd.recipient_id
            and zce.status = 'completed'
            and zce.created_at > fd.first_claimed_at
            and zce.created_at <= fd.first_claimed_at + interval '7' day
        group by 1
    ),

    -- CashExchange orders (customer-side)
    ce_txns as (
        select fd.recipient_id,
               'cash_exchange' as tx_type,
               count(*) as tx_count,
               round((sum(t.amount) / 1e6)::numeric, 2) as tx_volume,
               min(t.posted_at) as first_tx_at
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.type = 'Transaction::CashExchange'
            and t.status = 3
            and t.metadata->>'role' = 'customer'
            and coalesce(t.metadata->>'cancelled', 'false') != 'true'
            and t.posted_at > fd.first_claimed_at
            and t.posted_at <= fd.first_claimed_at + interval '7' day
        group by 1
    ),

    all_txns as (
        select * from cn_txns
        union all
        select * from card_txns
        union all
        select * from bt_txns
        union all
        select * from zce_txns
        union all
        select * from ce_txns
    )

    select at.recipient_id::text,
           at.tx_type,
           at.tx_count,
           at.tx_volume,
           (at.first_tx_at + interval '5' hour)::timestamp::text as first_tx_at
    from all_txns at
    order by at.recipient_id, at.tx_type
    """


# ── Query 7: Time to First Transaction (EXP-007) ────────────────────

def time_to_first_tx_query() -> str:
    """Per-recipient: earliest transaction timestamp and hours delta.

    Atlas Five Questions:
      Metric:  first transaction timestamp per recipient (any type)
      Entity:  all demo dollar recipients
      Time:    7 days post-demo receipt
      Group:   per recipient_id
      Output:  recipient_id, demo_date, first_tx_date, tx_type, hours_to_first_tx
    """
    return f"""
    with {ambassadors_cte()},
    {demo_dollars_cte()},

    first_demo as (
        select dd.recipient_id,
               min(dd.claimed_at) as first_claimed_at
        from demo_dollars dd
        group by 1
    ),

    -- Per-type first tx timestamps (7-day window)
    first_cn as (
        select fd.recipient_id,
               min(dcn.created_at) as first_ts,
               'cn_send' as tx_type
        from first_demo fd
        inner join digital_cash_notes dcn on dcn.depositor_id = fd.recipient_id
            and dcn.status = 'claimed'
            and dcn.created_at > fd.first_claimed_at
            and dcn.created_at <= fd.first_claimed_at + interval '7' day
            and dcn.claimant_id not in (select ambassador_id from ambassadors)
        group by 1
    ),

    first_card as (
        select fd.recipient_id,
               min(t.posted_at) as first_ts,
               'card_spend' as tx_type
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::CardSpend'
            and t.posted_at > fd.first_claimed_at
            and t.posted_at <= fd.first_claimed_at + interval '7' day
        group by 1
    ),

    first_bt as (
        select fd.recipient_id,
               min(t.posted_at) as first_ts,
               'bank_transfer' as tx_type
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::BankTransfer'
            and t.posted_at > fd.first_claimed_at
            and t.posted_at <= fd.first_claimed_at + interval '7' day
        group by 1
    ),

    first_zce as (
        select fd.recipient_id,
               min(zce.created_at) as first_ts,
               'zce_order' as tx_type
        from first_demo fd
        inner join zar_cash_exchange_orders zce on zce.initiator_id = fd.recipient_id
            and zce.status = 'completed'
            and zce.created_at > fd.first_claimed_at
            and zce.created_at <= fd.first_claimed_at + interval '7' day
        group by 1
    ),

    first_ce as (
        select fd.recipient_id,
               min(t.posted_at) as first_ts,
               'cash_exchange' as tx_type
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.type = 'Transaction::CashExchange'
            and t.status = 3
            and t.metadata->>'role' = 'customer'
            and coalesce(t.metadata->>'cancelled', 'false') != 'true'
            and t.posted_at > fd.first_claimed_at
            and t.posted_at <= fd.first_claimed_at + interval '7' day
        group by 1
    ),

    all_firsts as (
        select * from first_cn
        union all
        select * from first_card
        union all
        select * from first_bt
        union all
        select * from first_zce
        union all
        select * from first_ce
    ),

    earliest as (
        select af.recipient_id, af.first_ts, af.tx_type,
               row_number() over (partition by af.recipient_id order by af.first_ts) as rn
        from all_firsts af
    )

    select fd.recipient_id::text,
           (fd.first_claimed_at + interval '5' hour)::date::text as demo_date,
           case when e.first_ts is not null
                then (e.first_ts + interval '5' hour)::date::text
                else null end as first_tx_date,
           e.tx_type as first_tx_type,
           case when e.first_ts is not null
                then round(extract(epoch from (e.first_ts - fd.first_claimed_at)) / 3600.0, 2)
                else null end as hours_to_first_tx
    from first_demo fd
    left join earliest e on e.recipient_id = fd.recipient_id and e.rn = 1
    order by fd.first_claimed_at, fd.recipient_id
    """


# ── Query 8: All Activity Timestamps (repeat session analysis) ──────

def all_activity_timestamps_query() -> str:
    """All qualifying activity timestamps per recipient (not just first).

    Used for repeat session analysis: return rate, multi-day engagement,
    session clustering.

    Atlas Five Questions:
      Metric:  all qualifying activity timestamps
      Entity:  all demo dollar recipients
      Time:    post-demo receipt, no upper bound
      Group:   per recipient_id, activity_type
      Output:  recipient_id, activity_type, activity_ts (PKT), hours_after_demo
    """
    return f"""
    with {ambassadors_cte()},
    {demo_dollars_cte()},

    first_demo as (
        select dd.recipient_id,
               min(dd.claimed_at) as first_claimed_at,
               min(dd.ambassador_id::text)::uuid as first_ambassador_id
        from demo_dollars dd
        group by 1
    ),

    -- All CN sends to non-ambassadors (individual rows, not aggregated)
    cn_events as (
        select fd.recipient_id,
               'cn_send' as activity_type,
               dcn.created_at as activity_ts_utc,
               fd.first_claimed_at
        from first_demo fd
        inner join digital_cash_notes dcn on dcn.depositor_id = fd.recipient_id
            and dcn.status = 'claimed'
            and dcn.created_at > fd.first_claimed_at
            and dcn.claimant_id not in (select ambassador_id from ambassadors)
    ),

    -- All card spends
    card_events as (
        select fd.recipient_id,
               'card_spend' as activity_type,
               t.posted_at as activity_ts_utc,
               fd.first_claimed_at
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::CardSpend'
            and t.posted_at > fd.first_claimed_at
    ),

    -- All bank transfers
    bt_events as (
        select fd.recipient_id,
               'bank_transfer' as activity_type,
               t.posted_at as activity_ts_utc,
               fd.first_claimed_at
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::BankTransfer'
            and t.posted_at > fd.first_claimed_at
    ),

    -- All ZCE orders (cash exchange)
    zce_events as (
        select fd.recipient_id,
               'zce_order' as activity_type,
               zce.created_at as activity_ts_utc,
               fd.first_claimed_at
        from first_demo fd
        inner join zar_cash_exchange_orders zce on zce.initiator_id = fd.recipient_id
            and zce.status = 'completed'
            and zce.created_at > fd.first_claimed_at
    ),

    -- All CashExchange orders (customer-side)
    ce_events as (
        select fd.recipient_id,
               'cash_exchange' as activity_type,
               t.posted_at as activity_ts_utc,
               fd.first_claimed_at
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.type = 'Transaction::CashExchange'
            and t.status = 3
            and t.metadata->>'role' = 'customer'
            and coalesce(t.metadata->>'cancelled', 'false') != 'true'
            and t.posted_at > fd.first_claimed_at
    ),

    all_events as (
        select * from cn_events
        union all
        select * from card_events
        union all
        select * from bt_events
        union all
        select * from zce_events
        union all
        select * from ce_events
    )

    select ae.recipient_id::text,
           ae.activity_type,
           (ae.activity_ts_utc + interval '5' hour)::timestamp::text as activity_ts,
           round(extract(epoch from (ae.activity_ts_utc - ae.first_claimed_at)) / 3600.0, 2) as hours_after_demo
    from all_events ae
    order by ae.recipient_id, ae.activity_ts_utc
    """


# ══════════════════════════════════════════════════════════════════════
# Diagnostic / Verification Queries (EXP-007)
#
# Self-contained — inline all CTEs so each query can be run standalone
# via Rube MCP without needing lib/sql.py imports.
# ══════════════════════════════════════════════════════════════════════

_EXCLUDED_IDS = (
    "'57d456f2-84f7-4db5-b5b8-4f494f29c9dc', '83845f51-170d-44b4-907b-68ba7e3a87d0', "
    "'bf1de49f-179a-400f-b023-2e73b57a59d9', 'aa46304d-8e5c-4e97-8ff0-c0906813ecf4', "
    "'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec', 'f8780ccb-3d67-46e5-baa8-0811c64c730d', "
    "'84c74165-5eb6-4e4f-8b23-06892c09bdbc', '110228ec-0e17-482e-a692-3a34bdb3ab65', "
    "'9520d1e5-a92e-49d8-9a9e-6747523e0ed7', 'f32dd3b4-cad1-487b-8c87-e4924117c050', "
    "'5fd86e56-6c6d-426f-818e-f85898ec8dbf', '274bff97-2c1b-4410-a79d-dd81f33f5c15', "
    "'1b397809-6185-4273-b098-7d86cc821bc4', '44e72414-f6bc-4975-83fa-3046e28e9a94', "
    "'a464fe4a-ed62-41ca-87f4-4ab48d3c4058', '0eb006a5-53a8-41c2-9cca-6c06dc1c2549', "
    "'0aac7e5e-ac3a-49a3-b588-6fed46ca6ade', '0bc7e11b-5741-44b0-9c70-16fb5a58c2ee', "
    "'958a4910-a20f-4a06-81d6-d458dcc3bf57'"
)


# ── Diagnostic 1: Verify Demo Universe ────────────────────────────────

def verify_demo_universe_query() -> str:
    """Every recipient in the demo universe with their demo details.

    Atlas Five Questions:
      Metric:  recipient demo details (who qualifies and why)
      Entity:  all demo dollar recipients
      Time:    Feb 1 2026+
      Group:   per recipient_id
      Output:  recipient_id, username, ambassador_name, demo_date,
               total_received, notes_count, is_onboarded, is_secured,
               account_created_date
    """
    return f"""
    with ambassadors as (
        select distinct uur.user_id as ambassador_id
        from user_to_user_roles uur
        inner join user_roles ur on ur.id = uur.user_role_id
        where ur.name = 'ambassador'
          and uur.user_id not in ({_EXCLUDED_IDS})
    ),

    demo_dollars as (
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
    ),

    recipient_base as (
        select dd.recipient_id,
               min(dd.ambassador_id::text)::uuid as first_ambassador_id,
               min(dd.claimed_date) as first_demo_date,
               sum(dd.amount_usd) as total_received,
               count(*) as notes_count
        from demo_dollars dd
        group by 1
    )

    select rb.recipient_id::text,
           u.username,
           coalesce(nullif(trim(concat(coalesce(ua.first_name,''),' ',coalesce(ua.last_name,''))), ''), ua.username, 'Unknown') as ambassador_name,
           rb.first_demo_date::text as demo_date,
           round(rb.total_received::numeric, 2) as total_received,
           rb.notes_count,
           (exists (
               select 1 from merchant_onboarding_submissions mos
               where mos.phone_number = u.phone_number
                 and mos.status in ('active', 'pending')
           ) or exists (
               select 1 from product_enrollments pe
               inner join product_definitions pd on pd.id = pe.product_definition_id
               where pe.user_id = rb.recipient_id
                 and pd.code = 'zar_cash_exchange_merchant'
                 and pe.state = 2
           )) as is_onboarded,
           case when (u.email is not null and u.email != '')
                  or (u.phone_number is not null and u.phone_number != '')
                then true else false end as is_secured,
           (u.created_at + interval '5' hour)::date::text as account_created_date
    from recipient_base rb
    inner join users u on u.id = rb.recipient_id
    left join users ua on ua.id = rb.first_ambassador_id
    order by rb.first_demo_date, rb.recipient_id
    """


# ── Diagnostic 2: Verify Recipient Activity ──────────────────────────

def verify_recipient_activity_query() -> str:
    """Re-run canonical activity query fully expanded (no lib imports).

    Atlas Five Questions:
      Metric:  post-demo activity counts and volumes per type
      Entity:  all demo dollar recipients
      Time:    post-demo receipt, no upper bound
      Group:   per recipient_id
      Output:  recipient_id, username, cn_send_to_amb_count/vol,
               cn_send_to_others_count/vol, card_count/vol, bt_count/vol,
               zce_count/vol
    """
    return f"""
    with ambassadors as (
        select distinct uur.user_id as ambassador_id
        from user_to_user_roles uur
        inner join user_roles ur on ur.id = uur.user_role_id
        where ur.name = 'ambassador'
          and uur.user_id not in ({_EXCLUDED_IDS})
    ),

    demo_dollars as (
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
    ),

    first_demo as (
        select dd.recipient_id,
               min(dd.claimed_at) as first_claimed_at,
               min(dd.ambassador_id::text)::uuid as first_ambassador_id
        from demo_dollars dd
        group by 1
    ),

    cn_sends_to_amb as (
        select fd.recipient_id,
               count(*) as cn_send_to_amb_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as cn_send_to_amb_volume
        from first_demo fd
        inner join digital_cash_notes dcn on dcn.depositor_id = fd.recipient_id
            and dcn.claimant_id = fd.first_ambassador_id
            and dcn.status = 'claimed'
            and dcn.created_at > fd.first_claimed_at
        group by 1
    ),

    cn_sends_to_others as (
        select fd.recipient_id,
               count(*) as cn_send_to_others_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as cn_send_to_others_volume
        from first_demo fd
        inner join digital_cash_notes dcn on dcn.depositor_id = fd.recipient_id
            and dcn.status = 'claimed'
            and dcn.created_at > fd.first_claimed_at
            and dcn.claimant_id not in (select ambassador_id from ambassadors)
        group by 1
    ),

    card_spend as (
        select fd.recipient_id,
               count(*) as card_count,
               round((sum(abs(t.amount)) / 1e6)::numeric, 2) as card_volume
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::CardSpend'
            and t.posted_at > fd.first_claimed_at
        group by 1
    ),

    bank_transfers as (
        select fd.recipient_id,
               count(*) as bt_count,
               round((sum(abs(t.amount)) / 1e6)::numeric, 2) as bt_volume
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.status = 3
            and t.type = 'Transaction::BankTransfer'
            and t.posted_at > fd.first_claimed_at
        group by 1
    ),

    zce_orders as (
        select fd.recipient_id,
               count(*) as zce_count,
               round((sum(zce.amount) / 1e6)::numeric, 2) as zce_volume
        from first_demo fd
        inner join zar_cash_exchange_orders zce on zce.initiator_id = fd.recipient_id
            and zce.status = 'completed'
            and zce.created_at > fd.first_claimed_at
        group by 1
    ),

    ce_orders as (
        select fd.recipient_id,
               count(*) as ce_count,
               round((sum(t.amount) / 1e6)::numeric, 2) as ce_volume
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.type = 'Transaction::CashExchange'
            and t.status = 3
            and t.metadata->>'role' = 'customer'
            and coalesce(t.metadata->>'cancelled', 'false') != 'true'
            and t.posted_at > fd.first_claimed_at
        group by 1
    )

    select fd.recipient_id::text,
           u.username,
           coalesce(csa.cn_send_to_amb_count, 0) as cn_send_to_amb_count,
           coalesce(csa.cn_send_to_amb_volume, 0) as cn_send_to_amb_volume,
           coalesce(cso.cn_send_to_others_count, 0) as cn_send_to_others_count,
           coalesce(cso.cn_send_to_others_volume, 0) as cn_send_to_others_volume,
           coalesce(cs.card_count, 0) as card_count,
           coalesce(cs.card_volume, 0) as card_volume,
           coalesce(bt.bt_count, 0) as bt_count,
           coalesce(bt.bt_volume, 0) as bt_volume,
           coalesce(zce.zce_count, 0) as zce_count,
           coalesce(zce.zce_volume, 0) as zce_volume,
           coalesce(ce.ce_count, 0) as ce_count,
           coalesce(ce.ce_volume, 0) as ce_volume
    from first_demo fd
    inner join users u on u.id = fd.recipient_id
    left join cn_sends_to_amb csa on csa.recipient_id = fd.recipient_id
    left join cn_sends_to_others cso on cso.recipient_id = fd.recipient_id
    left join card_spend cs on cs.recipient_id = fd.recipient_id
    left join bank_transfers bt on bt.recipient_id = fd.recipient_id
    left join zce_orders zce on zce.recipient_id = fd.recipient_id
    left join ce_orders ce on ce.recipient_id = fd.recipient_id
    order by fd.recipient_id
    """


# ── Diagnostic 3: All Transactions (any type/status) ─────────────────

def diagnose_all_transactions_query() -> str:
    """All transactions (any type, any status) for demo recipients.

    Catches transaction types we might be missing in the tier logic
    (e.g. DigitalCashTransfer, TokenTransfer).

    Atlas Five Questions:
      Metric:  transaction count and volume by type and status
      Entity:  all demo dollar recipients
      Time:    post-demo receipt, no upper bound
      Group:   per recipient_id, tx_type, tx_status
      Output:  recipient_id, username, tx_type, tx_status, tx_count,
               volume_usd, first_tx, last_tx
    """
    return f"""
    with ambassadors as (
        select distinct uur.user_id as ambassador_id
        from user_to_user_roles uur
        inner join user_roles ur on ur.id = uur.user_role_id
        where ur.name = 'ambassador'
          and uur.user_id not in ({_EXCLUDED_IDS})
    ),

    demo_dollars as (
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
    ),

    first_demo as (
        select dd.recipient_id,
               min(dd.claimed_at) as first_claimed_at
        from demo_dollars dd
        group by 1
    )

    select fd.recipient_id::text,
           u.username,
           t.type as tx_type,
           t.status as tx_status,
           count(*) as tx_count,
           round((sum(abs(t.amount)) / 1e6)::numeric, 2) as volume_usd,
           min((t.posted_at + interval '5' hour)::timestamp)::text as first_tx,
           max((t.posted_at + interval '5' hour)::timestamp)::text as last_tx
    from first_demo fd
    inner join users u on u.id = fd.recipient_id
    inner join transactions t on t.user_id = fd.recipient_id
        and t.posted_at > fd.first_claimed_at
    group by 1, 2, 3, 4
    order by 1, 3, 4
    """


# ── Diagnostic 4: All Cash Notes (sent + received, all statuses) ─────

def diagnose_all_cash_notes_query() -> str:
    """All cash notes involving demo recipients (as sender AND receiver).

    Catches CN activity beyond just "sent to non-ambassador" and
    "sent to ambassador" — e.g. pending/expired notes, received notes
    from non-ambassadors.

    Atlas Five Questions:
      Metric:  cash note count and volume by direction and status
      Entity:  all demo dollar recipients
      Time:    post-demo receipt, no upper bound
      Group:   per recipient_id, direction, cn_status
      Output:  recipient_id, username, direction, cn_status, note_count,
               volume_usd, first_ts, last_ts
    """
    return f"""
    with ambassadors as (
        select distinct uur.user_id as ambassador_id
        from user_to_user_roles uur
        inner join user_roles ur on ur.id = uur.user_role_id
        where ur.name = 'ambassador'
          and uur.user_id not in ({_EXCLUDED_IDS})
    ),

    demo_dollars as (
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
    ),

    first_demo as (
        select dd.recipient_id,
               min(dd.claimed_at) as first_claimed_at
        from demo_dollars dd
        group by 1
    ),

    -- Notes SENT by recipients (depositor)
    sent_notes as (
        select fd.recipient_id,
               'sent' as direction,
               dcn.status as cn_status,
               count(*) as note_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as volume_usd,
               min((dcn.created_at + interval '5' hour)::timestamp)::text as first_ts,
               max((dcn.created_at + interval '5' hour)::timestamp)::text as last_ts
        from first_demo fd
        inner join digital_cash_notes dcn on dcn.depositor_id = fd.recipient_id
            and dcn.created_at > fd.first_claimed_at
        group by 1, 2, 3
    ),

    -- Notes RECEIVED by recipients (claimant) — excluding original demo notes
    received_notes as (
        select fd.recipient_id,
               'received' as direction,
               dcn.status as cn_status,
               count(*) as note_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as volume_usd,
               min((dcn.created_at + interval '5' hour)::timestamp)::text as first_ts,
               max((dcn.created_at + interval '5' hour)::timestamp)::text as last_ts
        from first_demo fd
        inner join digital_cash_notes dcn on dcn.claimant_id = fd.recipient_id
            and dcn.created_at > fd.first_claimed_at
            and dcn.id not in (select note_id from demo_dollars)
        group by 1, 2, 3
    ),

    all_cn as (
        select * from sent_notes
        union all
        select * from received_notes
    )

    select ac.recipient_id::text,
           u.username,
           ac.direction,
           ac.cn_status,
           ac.note_count,
           ac.volume_usd,
           ac.first_ts,
           ac.last_ts
    from all_cn ac
    inner join users u on u.id = ac.recipient_id::uuid
    order by ac.recipient_id, ac.direction, ac.cn_status
    """


# ── Diagnostic 5: All ZCE Orders ─────────────────────────────────────

def diagnose_all_zce_query() -> str:
    """All ZCE orders + CashExchange involving demo recipients (as initiator AND fulfiller).

    Atlas Five Questions:
      Metric:  ZCE/CashExchange order count and volume by role and status
      Entity:  all demo dollar recipients
      Time:    post-demo receipt, no upper bound
      Group:   per recipient_id, role, order_status
      Output:  recipient_id, username, role, order_status, order_count,
               volume_usd
    """
    return f"""
    with ambassadors as (
        select distinct uur.user_id as ambassador_id
        from user_to_user_roles uur
        inner join user_roles ur on ur.id = uur.user_role_id
        where ur.name = 'ambassador'
          and uur.user_id not in ({_EXCLUDED_IDS})
    ),

    demo_dollars as (
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
    ),

    first_demo as (
        select dd.recipient_id,
               min(dd.claimed_at) as first_claimed_at
        from demo_dollars dd
        group by 1
    ),

    -- ZCE as initiator (buyer)
    zce_initiator as (
        select fd.recipient_id,
               'initiator' as role,
               zce.status as zce_status,
               count(*) as order_count,
               round((sum(zce.amount) / 1e6)::numeric, 2) as volume_usd
        from first_demo fd
        inner join zar_cash_exchange_orders zce on zce.initiator_id = fd.recipient_id
            and zce.created_at > fd.first_claimed_at
        group by 1, 2, 3
    ),

    -- ZCE as fulfiller (merchant/seller)
    zce_fulfiller as (
        select fd.recipient_id,
               'fulfiller' as role,
               zce.status as zce_status,
               count(*) as order_count,
               round((sum(zce.amount) / 1e6)::numeric, 2) as volume_usd
        from first_demo fd
        inner join zar_cash_exchange_orders zce on zce.fulfiller_id = fd.recipient_id
            and zce.created_at > fd.first_claimed_at
        group by 1, 2, 3
    ),

    -- CashExchange as customer
    ce_customer as (
        select fd.recipient_id,
               'ce_customer' as role,
               t.status::text as zce_status,
               count(*) as order_count,
               round((sum(t.amount) / 1e6)::numeric, 2) as volume_usd
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.type = 'Transaction::CashExchange'
            and t.metadata->>'role' = 'customer'
            and t.posted_at > fd.first_claimed_at
        group by 1, 2, 3
    ),

    -- CashExchange as merchant
    ce_merchant as (
        select fd.recipient_id,
               'ce_merchant' as role,
               t.status::text as zce_status,
               count(*) as order_count,
               round((sum(t.amount) / 1e6)::numeric, 2) as volume_usd
        from first_demo fd
        inner join transactions t on t.user_id = fd.recipient_id
            and t.type = 'Transaction::CashExchange'
            and t.metadata->>'role' = 'merchant'
            and t.posted_at > fd.first_claimed_at
        group by 1, 2, 3
    ),

    all_zce as (
        select * from zce_initiator
        union all
        select * from zce_fulfiller
        union all
        select * from ce_customer
        union all
        select * from ce_merchant
    )

    select az.recipient_id::text,
           u.username,
           az.role,
           az.zce_status,
           az.order_count,
           az.volume_usd
    from all_zce az
    inner join users u on u.id = az.recipient_id::uuid
    order by az.recipient_id, az.role, az.zce_status
    """


# ── Diagnostic 6½: Note Detail (per-note rows with sequence) ─────────

def note_detail_query() -> str:
    """Per-note row for each demo dollar: recipient, note timestamp, sequence, amount, ambassador.

    Used for inter-visit tier analysis: compute engagement tier using only
    activity between the first and second demo note (not the full post-demo window).

    Atlas Five Questions:
      Metric:  individual demo dollar note details with sequence number
      Entity:  all demo dollar recipients
      Time:    Feb 1 2026+
      Group:   per recipient_id, per note
      Output:  recipient_id, note_id, claimed_at (PKT), amount_usd,
               ambassador_id, ambassador_name, note_num
    """
    return f"""
    with {ambassadors_cte()},
    {demo_dollars_cte()}

    select dd.recipient_id::text,
           dd.note_id::text,
           (dd.claimed_at + interval '5' hour)::timestamp::text as claimed_at_pkt,
           dd.amount_usd,
           dd.ambassador_id::text,
           coalesce(nullif(trim(concat(coalesce(ua.first_name,''),' ',coalesce(ua.last_name,''))), ''), ua.username, 'Unknown') as ambassador_name,
           row_number() over (partition by dd.recipient_id order by dd.claimed_at) as note_num
    from demo_dollars dd
    left join users ua on ua.id = dd.ambassador_id
    order by dd.recipient_id, dd.claimed_at
    """


# ── Diagnostic 6: Onboarding Status ──────────────────────────────────

def diagnose_onboarding_status_query() -> str:
    """Re-verify onboarding classification for all demo recipients.

    Shows both MOS and PE enrollment states (including non-qualifying
    states like pending enrollment).

    Atlas Five Questions:
      Metric:  onboarding status via MOS and PE pathways
      Entity:  all demo dollar recipients
      Time:    current state (no time filter)
      Group:   per recipient_id
      Output:  recipient_id, username, phone, has_mos, mos_statuses,
               has_pe, pe_states
    """
    return f"""
    with ambassadors as (
        select distinct uur.user_id as ambassador_id
        from user_to_user_roles uur
        inner join user_roles ur on ur.id = uur.user_role_id
        where ur.name = 'ambassador'
          and uur.user_id not in ({_EXCLUDED_IDS})
    ),

    demo_dollars as (
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
    ),

    recipients as (
        select distinct dd.recipient_id
        from demo_dollars dd
    ),

    mos_status as (
        select r.recipient_id,
               string_agg(distinct mos.status, ', ' order by mos.status) as mos_statuses
        from recipients r
        inner join users u on u.id = r.recipient_id
        inner join merchant_onboarding_submissions mos on mos.phone_number = u.phone_number
        group by 1
    ),

    pe_status as (
        select r.recipient_id,
               string_agg(distinct pe.state::text, ', ' order by pe.state::text) as pe_states
        from recipients r
        inner join product_enrollments pe on pe.user_id = r.recipient_id
        inner join product_definitions pd on pd.id = pe.product_definition_id
            and pd.code = 'zar_cash_exchange_merchant'
        group by 1
    )

    select r.recipient_id::text,
           u.username,
           u.phone_number as phone,
           mos.mos_statuses is not null as has_mos,
           coalesce(mos.mos_statuses, '') as mos_statuses,
           pe.pe_states is not null as has_pe,
           coalesce(pe.pe_states, '') as pe_states
    from recipients r
    inner join users u on u.id = r.recipient_id
    left join mos_status mos on mos.recipient_id = r.recipient_id
    left join pe_status pe on pe.recipient_id = r.recipient_id
    order by r.recipient_id
    """
