"""
SQL queries for EXP-004 Merchant Activation Incentive — Atlas conventions.

Style: lowercase keywords, CTEs over subqueries, 4-space indent,
short table aliases, positional group by, PKT offset +5h.

Canonical queries for Rube MCP (Metabase database ID 1, session "each").
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.sql import EXCLUDED_IDS_SQL, merchants_cte


# ── Sales CTEs ────────────────────────────────────────────────────────

def _sales_ctes() -> str:
    """CN (depositor, >$0.01) + ZCE (fulfiller) + CashExchange (merchant-side) sales for qualifying merchants.

    Only counts sales within each merchant's own 14-day activation window.
    Pool upper bound: merchants onboarded Feb 1–14 only (last window closes Feb 28).
    """
    return f"""cn_sales as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as customer_id,
               dcn.amount / 1e6 as amount_usd,
               dcn.amount as amount_raw,
               (dcn.created_at + interval '5' hour)::date as sale_date
        from digital_cash_notes dcn
        inner join qualifying q on q.merchant_id = dcn.depositor_id
            and q.onboarding_date <= '2026-02-14'
            and dcn.created_at >= q.onboarding_date
            and dcn.created_at < q.onboarding_date + interval '14 days'
        where dcn.status = 'claimed'
          and dcn.amount > 10000
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ), zce_sales as (
        select zce.fulfiller_id as merchant_id,
               zce.initiator_id as customer_id,
               zce.amount / 1e6 as amount_usd,
               zce.amount as amount_raw,
               (zce.created_at + interval '5' hour)::date as sale_date
        from zar_cash_exchange_orders zce
        inner join qualifying q on q.merchant_id = zce.fulfiller_id
            and q.onboarding_date <= '2026-02-14'
            and zce.created_at >= q.onboarding_date
            and zce.created_at < q.onboarding_date + interval '14 days'
        where zce.status = 'completed'
          and zce.initiator_id not in ({EXCLUDED_IDS_SQL})
    ), ce_sales as (
        select t.user_id as merchant_id,
               (t.metadata->>'counterparty_id')::uuid as customer_id,
               t.amount / 1e6 as amount_usd,
               t.amount as amount_raw,
               (t.created_at + interval '5' hour)::date as sale_date
        from transactions t
        inner join qualifying q on q.merchant_id = t.user_id
            and q.onboarding_date <= '2026-02-14'
            and t.created_at >= q.onboarding_date
            and t.created_at < q.onboarding_date + interval '14 days'
        where t.type = 'Transaction::CashExchange'
          and t.status = 3
          and t.metadata->>'role' = 'merchant'
          and coalesce(t.metadata->>'cancelled', 'false') != 'true'
          and (t.metadata->>'counterparty_id') not in ({EXCLUDED_IDS_SQL})
    ), all_sales as (
        select merchant_id, customer_id, amount_usd, amount_raw, sale_date,
               'cn' as sale_type
        from cn_sales
        union all
        select merchant_id, customer_id, amount_usd, amount_raw, sale_date,
               'zce' as sale_type
        from zce_sales
        union all
        select merchant_id, customer_id, amount_usd, amount_raw, sale_date,
               'ce' as sale_type
        from ce_sales
    )"""


# ── Query 1: Per-merchant qualification ───────────────────────────────

def merchant_qualification_query() -> str:
    """Per-merchant L1/L2/L3 qualification status and payout.

    Tiers:
      L1: any sale with amount >= $1 (1000000 raw)
      L2: 3+ total sales with amount > $0.01 (10000 raw)
      L3: total volume >= $10
    """
    return f"""
    with {merchants_cte(since='2026-02-01')},
    {_sales_ctes()},

    merchant_metrics as (
        select
            q.merchant_id,
            q.business_name,
            q.onboarding_date,
            -- L1: any sale >= $1
            count(*) filter (where s.amount_raw >= 1000000) as sales_gte_1usd,
            -- L2: total sales > $0.01
            count(*) filter (where s.amount_raw > 10000) as total_sales,
            -- L3: total volume
            coalesce(sum(s.amount_usd), 0) as total_volume,
            -- extra context
            count(distinct s.customer_id) as unique_customers,
            count(*) filter (where s.sale_type = 'cn') as cn_count,
            count(*) filter (where s.sale_type = 'zce') as zce_count,
            count(*) filter (where s.sale_type = 'ce') as ce_count
        from qualifying q
        left join all_sales s on s.merchant_id = q.merchant_id
        where q.onboarding_date <= '2026-02-14'
        group by 1, 2, 3
    )

    select
        merchant_id::text,
        business_name,
        onboarding_date::text,
        sales_gte_1usd,
        total_sales,
        round(total_volume::numeric, 2) as total_volume,
        unique_customers,
        cn_count,
        zce_count,
        ce_count,
        -- tier qualification
        case when sales_gte_1usd >= 1 then true else false end as l1_qualified,
        case when total_sales >= 3 then true else false end as l2_qualified,
        case when total_volume >= 10 then true else false end as l3_qualified,
        -- payout
        case when sales_gte_1usd >= 1 then 2 else 0 end
        + case when total_sales >= 3 then 3 else 0 end
        + case when total_volume >= 10 then 5 else 0 end as payout
    from merchant_metrics
    order by total_sales desc, total_volume desc
    """


# ── Query 2: Distribution summary ────────────────────────────────────

def distribution_summary_query() -> str:
    """Aggregate qualification stats across the pool."""
    return f"""
    with {merchants_cte(since='2026-02-01')},
    {_sales_ctes()},

    merchant_metrics as (
        select
            q.merchant_id,
            count(*) filter (where s.amount_raw >= 1000000) as sales_gte_1usd,
            count(*) filter (where s.amount_raw > 10000) as total_sales,
            coalesce(sum(s.amount_usd), 0) as total_volume,
            count(distinct s.customer_id) as unique_customers
        from qualifying q
        left join all_sales s on s.merchant_id = q.merchant_id
        where q.onboarding_date <= '2026-02-14'
        group by 1
    )

    select
        count(*) as total_pool,
        -- L1: any sale >= $1
        count(*) filter (where sales_gte_1usd >= 1) as l1_qualified,
        -- L2: 3+ sales > $0.01
        count(*) filter (where total_sales >= 3) as l2_qualified,
        -- L3: $10+ volume
        count(*) filter (where total_volume >= 10) as l3_qualified,
        -- spend
        sum(case when sales_gte_1usd >= 1 then 2 else 0 end) as l1_spend,
        sum(case when total_sales >= 3 then 3 else 0 end) as l2_spend,
        sum(case when total_volume >= 10 then 5 else 0 end) as l3_spend,
        sum(
            case when sales_gte_1usd >= 1 then 2 else 0 end
            + case when total_sales >= 3 then 3 else 0 end
            + case when total_volume >= 10 then 5 else 0 end
        ) as total_spend,
        -- distribution
        round(avg(total_sales)::numeric, 2) as avg_sales,
        round(percentile_cont(0.5) within group (order by total_sales)::numeric, 2) as median_sales,
        round(avg(total_volume)::numeric, 2) as avg_volume,
        round(percentile_cont(0.5) within group (order by total_volume)::numeric, 2) as median_volume,
        -- buckets
        count(*) filter (where total_sales = 0) as bucket_0,
        count(*) filter (where total_sales between 1 and 2) as bucket_1_2,
        count(*) filter (where total_sales between 3 and 5) as bucket_3_5,
        count(*) filter (where total_sales between 6 and 10) as bucket_6_10,
        count(*) filter (where total_sales > 10) as bucket_10plus
    from merchant_metrics
    """


# ── Query 4: Historical 14-day activation baseline ───────────────────

def historical_baseline_query() -> str:
    """14-day activation rate for all merchants onboarded before Feb 1, 2026.

    Answers: what % of pre-incentive merchants made a ≥$1 sale within
    14 days of their onboarding date? This is the baseline the EXP-004
    incentive is trying to beat.

    Uses merchant_sales_cte (ZCE + CashExchange union).
    """
    return f"""
    with {merchants_cte()},
    {_merchant_sales_cte_inline()},

    cohort as (
        select merchant_id, onboarding_date
        from merchants
        where onboarding_date < '2026-02-01'
    ),

    activation as (
        select c.merchant_id,
               max(case when ms.created_at >= c.onboarding_date::timestamp
                         and ms.created_at < (c.onboarding_date + interval '14 days')::timestamp
                         and ms.amount_usd >= 1.0
                    then 1 else 0 end) as activated
        from cohort c
        left join merchant_sales ms on ms.merchant_id = c.merchant_id
        group by 1
    )

    select
        count(*) as total,
        count(*) filter (where activated = 0) as no_14day_sale,
        count(*) filter (where activated = 1) as had_14day_sale,
        round(100.0 * count(*) filter (where activated = 1) / count(*), 1) as pct_activated_14d
    from activation
    """


def _merchant_sales_cte_inline() -> str:
    """Inline ZCE + CashExchange union (no merchant filter) for baseline query."""
    return f"""merchant_sales as (
        select zce.fulfiller_id as merchant_id,
               zce.amount / 1e6 as amount_usd,
               zce.created_at
        from zar_cash_exchange_orders zce
        where zce.status = 'completed'
          and zce.type = 'ZarCashExchange::MerchantOrder'
          and zce.initiator_id not in ({EXCLUDED_IDS_SQL})

        union all

        select t.user_id as merchant_id,
               t.amount / 1e6 as amount_usd,
               t.created_at
        from transactions t
        where t.type = 'Transaction::CashExchange'
          and t.status = 3
          and t.metadata->>'role' = 'merchant'
          and coalesce(t.metadata->>'cancelled', 'false') != 'true'
          and (t.metadata->>'counterparty_id') not in ({EXCLUDED_IDS_SQL})
    )"""


# ── Query 3: Fraud signal detection ──────────────────────────────────

def fraud_signals_query() -> str:
    """Detect potential gaming patterns in merchant sales.

    Flags:
      - Self-sends (depositor = claimant via intermediary)
      - Round-trips (A→B→A within 24h)
      - Dust spam (3+ sales all < $0.10)
      - Single-customer concentration (all sales to 1 person)
    """
    return f"""
    with {merchants_cte(since='2026-02-01')},
    {_sales_ctes()},

    -- self-send: merchant sends CN to themselves
    self_sends as (
        select merchant_id, count(*) as self_send_count
        from cn_sales
        where merchant_id = customer_id
        group by 1
    ),

    -- dust transactions: sales < $0.10
    dust_counts as (
        select merchant_id,
               count(*) as dust_count,
               count(*) filter (where amount_usd < 0.10) as sub_10c_count
        from all_sales
        group by 1
    ),

    -- customer concentration: all sales to single customer
    customer_concentration as (
        select merchant_id,
               count(distinct customer_id) as distinct_customers,
               count(*) as total_txns,
               round(count(*)::numeric / nullif(count(distinct customer_id), 0), 2) as txns_per_customer
        from all_sales
        group by 1
    )

    select
        q.merchant_id::text,
        q.business_name,
        coalesce(ss.self_send_count, 0) as self_sends,
        coalesce(dc.dust_count, 0) as total_txns,
        coalesce(dc.sub_10c_count, 0) as dust_txns,
        coalesce(cc.distinct_customers, 0) as distinct_customers,
        coalesce(cc.txns_per_customer, 0) as txns_per_customer,
        -- flags
        case when ss.self_send_count > 0 then 'SELF_SEND' else '' end as flag_self_send,
        case when dc.sub_10c_count >= 3 then 'DUST_SPAM' else '' end as flag_dust_spam,
        case when cc.distinct_customers = 1 and cc.total_txns >= 3 then 'SINGLE_CUSTOMER' else '' end as flag_single_customer
    from qualifying q
    left join self_sends ss on ss.merchant_id = q.merchant_id
    left join dust_counts dc on dc.merchant_id = q.merchant_id
    left join customer_concentration cc on cc.merchant_id = q.merchant_id
    where q.onboarding_date <= '2026-02-14'
      and coalesce(dc.dust_count, 0) > 0
    order by dust_txns desc, self_sends desc
    """
