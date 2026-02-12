"""
SQL queries for merchant-user onboarding analysis — Atlas conventions.

Style: lowercase keywords, CTEs over subqueries, 4-space indent,
short table aliases (no AS), positional group by, PKT offset +5h.

These are the canonical queries for this experiment. run.py reads from
cache but these are here for direct fetching via Rube MCP.
"""

# ── Shared constants ──────────────────────────────────────────────────

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


def _merchants_cte() -> str:
    """Shared merchants CTE used by all query functions."""
    return f"""merchants as (
        select distinct on (u.id)
               u.id as merchant_id, mos.business_name,
               mos.city, mos.latitude, mos.longitude, mos.status,
               (mos.created_at + interval '5' hour)::date as onboarding_date,
               u_onb.username as onboarder_username,
               coalesce(nullif(trim(concat(coalesce(u_onb.first_name,''),' ',coalesce(u_onb.last_name,''))), ''), 'Unknown') as onboarder_name
        from merchant_onboarding_submissions mos
        inner join users u on u.phone_number = mos.phone_number
        left join users u_onb on u_onb.id = mos.onboarder_id
        where mos.status in ('active', 'pending')
          and lower(mos.business_name) not like '%test%'
          and u.id not in ({EXCLUDED_IDS_SQL})
        order by u.id, mos.created_at desc
    )"""


# ── Legacy date-scoped queries (kept for reference) ──────────────────

def merchant_summary_query(start_date: str, end_date: str) -> str:
    """Per-merchant summary: onboarding info + CN sent + ZCE + bank transfers + card txns + activation + onboarding detail + tier earnings."""
    return f"""
    -- 1. Base merchants (phone_number join to capture merchants where merchant_id is null)
    with {_merchants_cte()},

    -- 2. Merchant activity (date-scoped)
    cash_notes_sent as (
        select dcn.depositor_id as merchant_id,
               count(*) as cn_count,
               count(distinct dcn.claimant_id) as cn_users,
               sum(dcn.amount) / 1e6 as cn_volume
        from digital_cash_notes dcn
        where dcn.status = 'claimed'
          and dcn.depositor_id is not null
          and (dcn.claimed_at + interval '5' hour)::date >= '{start_date}'
          and (dcn.claimed_at + interval '5' hour)::date <= '{end_date}'
        group by 1
    ),
    zce_fulfilled as (
        select zce.fulfiller_id as merchant_id,
               count(*) as zce_count,
               count(distinct zce.initiator_id) as zce_users,
               sum(zce.amount) / 1e6 as zce_volume
        from zar_cash_exchange_orders zce
        where zce.status = 'completed'
          and zce.fulfiller_id is not null
          and (zce.completed_at + interval '5' hour)::date >= '{start_date}'
          and (zce.completed_at + interval '5' hour)::date <= '{end_date}'
        group by 1
    ),
    bank_transfers as (
        select t.user_id as merchant_id,
               count(*) as bt_count,
               sum(t.amount) / 1e6 as bt_volume
        from transactions t
        where t.status = 3
          and t.type = 'Transaction::BankTransfer'
          and (t.posted_at + interval '5' hour)::date >= '{start_date}'
          and (t.posted_at + interval '5' hour)::date <= '{end_date}'
        group by 1
    ),
    card_transactions as (
        select t.user_id as merchant_id,
               count(*) as card_count,
               sum(t.amount) / 1e6 as card_volume
        from transactions t
        where t.status = 3
          and t.type = 'Transaction::CardSpend'
          and (t.posted_at + interval '5' hour)::date >= '{start_date}'
          and (t.posted_at + interval '5' hour)::date <= '{end_date}'
        group by 1
    ),
    user_activity as (
        select merchant_id from (
            select user_id as merchant_id from transactions
            where status = 3
              and (posted_at + interval '5' hour)::date >= '{start_date}'
              and (posted_at + interval '5' hour)::date <= '{end_date}'
            union
            select claimant_id from digital_cash_notes
            where status = 'claimed'
              and (claimed_at + interval '5' hour)::date >= '{start_date}'
              and (claimed_at + interval '5' hour)::date <= '{end_date}'
            union
            select depositor_id from digital_cash_notes
            where (created_at + interval '5' hour)::date >= '{start_date}'
              and (created_at + interval '5' hour)::date <= '{end_date}'
        ) x
        where merchant_id is not null
        group by 1
    ),

    -- 3. User onboarding (merchant-scoped)
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at,
               dcn.id as onboarding_note_id
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and (dcn.claimed_at + interval '5' hour)::date >= '{start_date}'
          and (dcn.claimed_at + interval '5' hour)::date <= '{end_date}'
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),
    merchant_onboarding as (
        select merchant_id,
               count(distinct user_id) as users_onboarded
        from onboarded_users_list
        group by 1
    ),

    -- 4a. Same-merchant return transactions (activation)
    user_merchant_txns as (
        -- Cash notes received from same merchant (user=claimant, merchant=depositor)
        select oul.user_id, oul.merchant_id, dcn.claimed_at as txn_time, dcn.id as txn_id
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.claimant_id = oul.user_id
            and dcn.depositor_id = oul.merchant_id
            and dcn.status = 'claimed'
            and dcn.id != oul.onboarding_note_id
            and dcn.claimed_at > oul.onboarding_claimed_at
        union all
        -- ZCE MerchantOrders at same merchant (user=initiator, merchant=fulfiller)
        select oul.user_id, oul.merchant_id, zceo.created_at, zceo.id
        from onboarded_users_list oul
        join zar_cash_exchange_orders zceo on zceo.initiator_id = oul.user_id
            and zceo.fulfiller_id = oul.merchant_id
            and zceo.status = 'completed'
            and zceo.type = 'ZarCashExchange::MerchantOrder'
            and zceo.created_at > oul.onboarding_claimed_at
    ),
    user_first_return as (
        select user_id, merchant_id,
               row_number() over (partition by user_id, merchant_id order by txn_time) as rn
        from user_merchant_txns
    ),
    merchant_activations as (
        select merchant_id, count(*) as activated_users
        from user_first_return where rn = 1
        group by 1
    ),

    -- 4b. Onboarded-user activity — any platform activity (CN send + card + bank transfer + ZCE)
    onboarded_transacting as (
        select merchant_id,
               count(distinct user_id) as transacting_users
        from (
            select oul.merchant_id, oul.user_id
            from onboarded_users_list oul
            join digital_cash_notes dcn on dcn.depositor_id = oul.user_id
                and dcn.status = 'claimed'
                and dcn.created_at > oul.onboarding_claimed_at
            union
            select oul.merchant_id, oul.user_id
            from onboarded_users_list oul
            join transactions t on t.user_id = oul.user_id
                and t.status = 3
                and t.type = 'Transaction::CardSpend'
                and t.posted_at > oul.onboarding_claimed_at
            union
            select oul.merchant_id, oul.user_id
            from onboarded_users_list oul
            join transactions t on t.user_id = oul.user_id
                and t.status = 3
                and t.type = 'Transaction::BankTransfer'
                and t.posted_at > oul.onboarding_claimed_at
            union
            select oul.merchant_id, oul.user_id
            from onboarded_users_list oul
            join zar_cash_exchange_orders zceo on zceo.initiator_id = oul.user_id
                and zceo.status = 'completed'
                and zceo.created_at > oul.onboarding_claimed_at
        ) active_users
        group by 1
    ),
    onboarded_cn_stats as (
        select oul.merchant_id,
               count(distinct oul.user_id) as tr_cn_users,
               count(*) as tr_cn_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as tr_cn_volume,
               round(percentile_cont(0.5) within group (order by dcn.amount / 1e6)::numeric, 2) as tr_cn_median
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.depositor_id = oul.user_id
            and dcn.status = 'claimed'
            and dcn.created_at > oul.onboarding_claimed_at
        group by 1
    ),
    onboarded_card_stats as (
        select oul.merchant_id,
               count(distinct oul.user_id) as tr_card_users,
               count(*) as tr_card_count,
               round((sum(t.amount) / 1e6)::numeric, 2) as tr_card_volume,
               round(percentile_cont(0.5) within group (order by t.amount / 1e6)::numeric, 2) as tr_card_median
        from onboarded_users_list oul
        join transactions t on t.user_id = oul.user_id
            and t.status = 3
            and t.type = 'Transaction::CardSpend'
            and t.posted_at > oul.onboarding_claimed_at
        group by 1
    ),
    onboarded_bt_stats as (
        select oul.merchant_id,
               count(distinct oul.user_id) as tr_bt_users,
               count(*) as tr_bt_count,
               round((sum(t.amount) / 1e6)::numeric, 2) as tr_bt_volume,
               round(percentile_cont(0.5) within group (order by t.amount / 1e6)::numeric, 2) as tr_bt_median
        from onboarded_users_list oul
        join transactions t on t.user_id = oul.user_id
            and t.status = 3
            and t.type = 'Transaction::BankTransfer'
            and t.posted_at > oul.onboarding_claimed_at
        group by 1
    ),

    -- 5. Lifetime (intentionally un-date-scoped)
    wallet_funding as (
        select dcn.claimant_id as user_id,
               sum(dcn.amount) / 1e6 as total_funded_usd
        from digital_cash_notes dcn
        where dcn.status = 'claimed'
        group by 1
    ),
    onboarded_secure as (
        select oul.merchant_id,
               count(distinct oul.user_id) as secure_users
        from onboarded_users_list oul
        join users u on u.id = oul.user_id
        where (u.email is not null and u.email != '')
           or (u.phone_number is not null and u.phone_number != '')
        group by 1
    ),

    -- 6. Tier-split aggregation for earnings model
    merchant_onboarding_tiers as (
        select merchant_id,
               count(distinct user_id) filter (
                   where (onboarding_claimed_at + interval '5' hour)::date < '2026-01-28'
               ) as onboarded_tier1,
               count(distinct user_id) filter (
                   where (onboarding_claimed_at + interval '5' hour)::date >= '2026-01-28'
               ) as onboarded_tier2
        from onboarded_users_list
        group by 1
    ),
    merchant_activations_tier2 as (
        select ufr.merchant_id, count(*) as activated_tier2
        from user_first_return ufr
        join onboarded_users_list oul on oul.user_id = ufr.user_id and oul.merchant_id = ufr.merchant_id
        where ufr.rn = 1
          and (oul.onboarding_claimed_at + interval '5' hour)::date >= '2026-01-28'
        group by 1
    )

    select m.merchant_id::text, m.business_name, m.city,
           m.latitude, m.longitude, m.status,
           m.onboarding_date::text as onboarding_date,
           m.onboarder_username, m.onboarder_name,
           coalesce(cn.cn_count, 0) as cn_count,
           coalesce(cn.cn_users, 0) as cn_users,
           coalesce(round(cn.cn_volume::numeric, 2), 0) as cn_volume,
           coalesce(zce.zce_count, 0) as zce_count,
           coalesce(zce.zce_users, 0) as zce_users,
           coalesce(round(zce.zce_volume::numeric, 2), 0) as zce_volume,
           coalesce(bt.bt_count, 0) as bt_count,
           coalesce(round(bt.bt_volume::numeric, 2), 0) as bt_volume,
           coalesce(ct.card_count, 0) as card_count,
           coalesce(round(ct.card_volume::numeric, 2), 0) as card_volume,
           case when ua.merchant_id is not null then true else false end as has_user_activity,
           coalesce(mo.users_onboarded, 0) as users_onboarded,
           coalesce(ma.activated_users, 0) as activated_users,
           coalesce(ot.transacting_users, 0) as transacting_users,
           coalesce(os.secure_users, 0) as secure_users,
           coalesce(round(wf.total_funded_usd::numeric, 2), 0) as wallet_funded_usd,
           coalesce(ocs.tr_cn_users, 0) as tr_cn_users,
           coalesce(ocs.tr_cn_count, 0) as tr_cn_count,
           coalesce(ocs.tr_cn_volume, 0) as tr_cn_volume,
           coalesce(ocs.tr_cn_median, 0) as tr_cn_median,
           coalesce(ocard.tr_card_users, 0) as tr_card_users,
           coalesce(ocard.tr_card_count, 0) as tr_card_count,
           coalesce(ocard.tr_card_volume, 0) as tr_card_volume,
           coalesce(ocard.tr_card_median, 0) as tr_card_median,
           coalesce(obt.tr_bt_users, 0) as tr_bt_users,
           coalesce(obt.tr_bt_count, 0) as tr_bt_count,
           coalesce(obt.tr_bt_volume, 0) as tr_bt_volume,
           coalesce(obt.tr_bt_median, 0) as tr_bt_median,
           coalesce(mot.onboarded_tier1, 0) as onboarded_tier1,
           coalesce(mot.onboarded_tier2, 0) as onboarded_tier2,
           coalesce(mat.activated_tier2, 0) as activated_tier2
    from merchants m
    left join cash_notes_sent cn on cn.merchant_id = m.merchant_id
    left join zce_fulfilled zce on zce.merchant_id = m.merchant_id
    left join bank_transfers bt on bt.merchant_id = m.merchant_id
    left join card_transactions ct on ct.merchant_id = m.merchant_id
    left join user_activity ua on ua.merchant_id = m.merchant_id
    left join merchant_onboarding mo on mo.merchant_id = m.merchant_id
    left join merchant_activations ma on ma.merchant_id = m.merchant_id
    left join onboarded_transacting ot on ot.merchant_id = m.merchant_id
    left join onboarded_secure os on os.merchant_id = m.merchant_id
    left join wallet_funding wf on wf.user_id = m.merchant_id
    left join onboarded_cn_stats ocs on ocs.merchant_id = m.merchant_id
    left join onboarded_card_stats ocard on ocard.merchant_id = m.merchant_id
    left join onboarded_bt_stats obt on obt.merchant_id = m.merchant_id
    left join merchant_onboarding_tiers mot on mot.merchant_id = m.merchant_id
    left join merchant_activations_tier2 mat on mat.merchant_id = m.merchant_id
    order by m.business_name
    """


# ── New granular queries (no date params — JS filters client-side) ───

def merchant_static_query() -> str:
    """One row per merchant with static fields (no date filtering)."""
    return f"""
    with {_merchants_cte()}
    select m.merchant_id::text, m.business_name, m.city,
           m.latitude, m.longitude, m.status,
           m.onboarding_date::text, m.onboarder_username, m.onboarder_name
    from merchants m
    order by m.business_name
    """


def user_onboardings_query() -> str:
    """One row per user onboarding event with transacting + secure flags."""
    return f"""
    with {_merchants_cte()},
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at,
               dcn.id as onboarding_note_id
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),
    transacting_users as (
        select distinct oul.user_id
        from onboarded_users_list oul
        where exists (
            select 1 from digital_cash_notes dcn
            where dcn.depositor_id = oul.user_id
              and dcn.status = 'claimed'
              and dcn.created_at > oul.onboarding_claimed_at
        )
        union
        select distinct oul.user_id
        from onboarded_users_list oul
        where exists (
            select 1 from transactions t
            where t.user_id = oul.user_id
              and t.status = 3
              and t.type = 'Transaction::CardSpend'
              and t.posted_at > oul.onboarding_claimed_at
        )
        union
        select distinct oul.user_id
        from onboarded_users_list oul
        where exists (
            select 1 from transactions t
            where t.user_id = oul.user_id
              and t.status = 3
              and t.type = 'Transaction::BankTransfer'
              and t.posted_at > oul.onboarding_claimed_at
        )
        union
        select distinct oul.user_id
        from onboarded_users_list oul
        where exists (
            select 1 from zar_cash_exchange_orders zceo
            where zceo.initiator_id = oul.user_id
              and zceo.status = 'completed'
              and zceo.created_at > oul.onboarding_claimed_at
        )
    ),
    secure_users as (
        select distinct oul.user_id
        from onboarded_users_list oul
        join users u on u.id = oul.user_id
        where (u.email is not null and u.email != '')
           or (u.phone_number is not null and u.phone_number != '')
    )
    select oul.merchant_id::text,
           oul.user_id::text,
           ((oul.onboarding_claimed_at + interval '5' hour)::date)::text as date,
           case when tu.user_id is not null then true else false end as is_transacting,
           case when su.user_id is not null then true else false end as is_secure
    from onboarded_users_list oul
    left join transacting_users tu on tu.user_id = oul.user_id
    left join secure_users su on su.user_id = oul.user_id
    order by oul.merchant_id, oul.onboarding_claimed_at
    """


def user_activations_query() -> str:
    """One row per user activation (first return to same merchant)."""
    return f"""
    with {_merchants_cte()},
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at,
               dcn.id as onboarding_note_id
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),
    user_merchant_txns as (
        select oul.user_id, oul.merchant_id, dcn.claimed_at as txn_time, dcn.id as txn_id,
               dcn.amount / 1e6 as amount, 'cash_note' as txn_type,
               oul.onboarding_claimed_at as onboard_time
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.claimant_id = oul.user_id
            and dcn.depositor_id = oul.merchant_id
            and dcn.status = 'claimed'
            and dcn.id != oul.onboarding_note_id
            and dcn.claimed_at > oul.onboarding_claimed_at
        union all
        select oul.user_id, oul.merchant_id, zceo.created_at, zceo.id,
               zceo.amount / 1e6 as amount, 'order' as txn_type,
               oul.onboarding_claimed_at as onboard_time
        from onboarded_users_list oul
        join zar_cash_exchange_orders zceo on zceo.initiator_id = oul.user_id
            and zceo.fulfiller_id = oul.merchant_id
            and zceo.status = 'completed'
            and zceo.type = 'ZarCashExchange::MerchantOrder'
            and zceo.created_at > oul.onboarding_claimed_at
    ),
    user_first_return as (
        select user_id, merchant_id, txn_time, amount, txn_type, onboard_time,
               row_number() over (partition by user_id, merchant_id order by txn_time) as rn
        from user_merchant_txns
    )
    select ufr.merchant_id::text,
           ufr.user_id::text,
           ((ufr.txn_time + interval '5' hour)::date)::text as date,
           round(ufr.amount::numeric, 2) as amount,
           ufr.txn_type,
           ((ufr.onboard_time + interval '5' hour)::date)::text as onboard_date
    from user_first_return ufr
    where ufr.rn = 1
    order by ufr.merchant_id, ufr.txn_time
    """


def merchant_daily_activity_query() -> str:
    """Daily activity per merchant: CN/ZCE/BT/card counts + volumes."""
    return f"""
    with {_merchants_cte()},
    cn_daily as (
        select dcn.depositor_id as merchant_id,
               (dcn.claimed_at + interval '5' hour)::date as date,
               count(*) as cn_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as cn_volume
        from digital_cash_notes dcn
        where dcn.status = 'claimed'
          and dcn.depositor_id in (select merchant_id from merchants)
        group by 1, 2
    ),
    zce_daily as (
        select zce.fulfiller_id as merchant_id,
               (zce.completed_at + interval '5' hour)::date as date,
               count(*) as zce_count,
               round((sum(zce.amount) / 1e6)::numeric, 2) as zce_volume
        from zar_cash_exchange_orders zce
        where zce.status = 'completed'
          and zce.fulfiller_id in (select merchant_id from merchants)
        group by 1, 2
    ),
    bt_daily as (
        select t.user_id as merchant_id,
               (t.posted_at + interval '5' hour)::date as date,
               count(*) as bt_count,
               round((sum(t.amount) / 1e6)::numeric, 2) as bt_volume
        from transactions t
        where t.status = 3
          and t.type = 'Transaction::BankTransfer'
          and t.user_id in (select merchant_id from merchants)
        group by 1, 2
    ),
    card_daily as (
        select t.user_id as merchant_id,
               (t.posted_at + interval '5' hour)::date as date,
               count(*) as card_count,
               round((sum(t.amount) / 1e6)::numeric, 2) as card_volume
        from transactions t
        where t.status = 3
          and t.type = 'Transaction::CardSpend'
          and t.user_id in (select merchant_id from merchants)
        group by 1, 2
    ),
    all_days as (
        select merchant_id, date from cn_daily
        union select merchant_id, date from zce_daily
        union select merchant_id, date from bt_daily
        union select merchant_id, date from card_daily
    )
    select ad.merchant_id::text, ad.date::text,
           coalesce(cn.cn_count, 0) as cn_count, coalesce(cn.cn_volume, 0) as cn_volume,
           coalesce(zce.zce_count, 0) as zce_count, coalesce(zce.zce_volume, 0) as zce_volume,
           coalesce(bt.bt_count, 0) as bt_count, coalesce(bt.bt_volume, 0) as bt_volume,
           coalesce(card.card_count, 0) as card_count, coalesce(card.card_volume, 0) as card_volume
    from all_days ad
    left join cn_daily cn on cn.merchant_id = ad.merchant_id and cn.date = ad.date
    left join zce_daily zce on zce.merchant_id = ad.merchant_id and zce.date = ad.date
    left join bt_daily bt on bt.merchant_id = ad.merchant_id and bt.date = ad.date
    left join card_daily card on card.merchant_id = ad.merchant_id and card.date = ad.date
    order by ad.merchant_id, ad.date
    """


def user_txn_breakdown_query() -> str:
    """One row per transacting onboarded user per merchant with per-type counts and volumes."""
    return f"""
    with {_merchants_cte()},
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at,
               dcn.id as onboarding_note_id
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),
    cn_txns as (
        select oul.merchant_id, oul.user_id,
               count(*) as cn_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as cn_volume
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.depositor_id = oul.user_id
            and dcn.status = 'claimed'
            and dcn.created_at > oul.onboarding_claimed_at
        group by 1, 2
    ),
    card_txns as (
        select oul.merchant_id, oul.user_id,
               count(*) as card_count,
               round((sum(abs(t.amount)) / 1e6)::numeric, 2) as card_volume
        from onboarded_users_list oul
        join transactions t on t.user_id = oul.user_id
            and t.status = 3
            and t.type = 'Transaction::CardSpend'
            and t.posted_at > oul.onboarding_claimed_at
        group by 1, 2
    ),
    bt_txns as (
        select oul.merchant_id, oul.user_id,
               count(*) as bt_count,
               round((sum(abs(t.amount)) / 1e6)::numeric, 2) as bt_volume
        from onboarded_users_list oul
        join transactions t on t.user_id = oul.user_id
            and t.status = 3
            and t.type = 'Transaction::BankTransfer'
            and t.posted_at > oul.onboarding_claimed_at
        group by 1, 2
    ),
    all_users as (
        select merchant_id, user_id from cn_txns
        union select merchant_id, user_id from card_txns
        union select merchant_id, user_id from bt_txns
    )
    select au.merchant_id::text, au.user_id::text,
           coalesce(cn.cn_count, 0) as cn_count,
           coalesce(cn.cn_volume, 0) as cn_volume,
           coalesce(ct.card_count, 0) as card_count,
           coalesce(ct.card_volume, 0) as card_volume,
           coalesce(bt.bt_count, 0) as bt_count,
           coalesce(bt.bt_volume, 0) as bt_volume
    from all_users au
    left join cn_txns cn on cn.merchant_id = au.merchant_id and cn.user_id = au.user_id
    left join card_txns ct on ct.merchant_id = au.merchant_id and ct.user_id = au.user_id
    left join bt_txns bt on bt.merchant_id = au.merchant_id and bt.user_id = au.user_id
    order by au.merchant_id, au.user_id
    """


def user_invitations_query() -> str:
    """One row per onboarded user who invited others (traditional referrals + CN onboardings)."""
    return f"""
    with {_merchants_cte()},
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),
    traditional_referrals as (
        select oul.merchant_id, oul.user_id,
               count(distinct ur.referee_id) as referral_count
        from onboarded_users_list oul
        join users_referrals ur on ur.referrer_id = oul.user_id
        group by 1, 2
    ),
    cn_onboardings as (
        select oul.merchant_id, oul.user_id,
               count(distinct dcn.claimant_id) as cn_onboarding_count
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.depositor_id = oul.user_id
            and dcn.status = 'claimed'
            and dcn.claimed_at is not null
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
            and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
        group by 1, 2
    ),
    all_inviters as (
        select merchant_id, user_id from traditional_referrals
        union select merchant_id, user_id from cn_onboardings
    )
    select ai.merchant_id::text, ai.user_id::text,
           coalesce(tr.referral_count, 0) as referral_count,
           coalesce(cn.cn_onboarding_count, 0) as cn_onboarding_count
    from all_inviters ai
    left join traditional_referrals tr on tr.merchant_id = ai.merchant_id and tr.user_id = ai.user_id
    left join cn_onboardings cn on cn.merchant_id = ai.merchant_id and cn.user_id = ai.user_id
    order by ai.merchant_id, ai.user_id
    """


def user_first_transactions_query() -> str:
    """One row per onboarded user with first debit and first credit after onboarding."""
    return f"""
    with {_merchants_cte()},
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at,
               dcn.id as onboarding_note_id
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),

    -- Debit sources: CN send, card, bank transfer, ZCE order
    debit_cn_send as (
        select oul.merchant_id, oul.user_id,
               min(dcn.created_at) as first_ts,
               'cn_send' as debit_type
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.depositor_id = oul.user_id
            and dcn.status = 'claimed'
            and dcn.created_at > oul.onboarding_claimed_at
        group by 1, 2
    ),
    debit_card as (
        select oul.merchant_id, oul.user_id,
               min(t.posted_at) as first_ts,
               'card' as debit_type
        from onboarded_users_list oul
        join transactions t on t.user_id = oul.user_id
            and t.status = 3
            and t.type = 'Transaction::CardSpend'
            and t.posted_at > oul.onboarding_claimed_at
        group by 1, 2
    ),
    debit_bt as (
        select oul.merchant_id, oul.user_id,
               min(t.posted_at) as first_ts,
               'bank_transfer' as debit_type
        from onboarded_users_list oul
        join transactions t on t.user_id = oul.user_id
            and t.status = 3
            and t.type = 'Transaction::BankTransfer'
            and t.posted_at > oul.onboarding_claimed_at
        group by 1, 2
    ),
    debit_zce as (
        select oul.merchant_id, oul.user_id,
               min(zceo.created_at) as first_ts,
               'zce_order' as debit_type
        from onboarded_users_list oul
        join zar_cash_exchange_orders zceo on zceo.initiator_id = oul.user_id
            and zceo.status = 'completed'
            and zceo.created_at > oul.onboarding_claimed_at
        group by 1, 2
    ),
    all_debits as (
        select merchant_id, user_id, first_ts, debit_type from debit_cn_send
        union all
        select merchant_id, user_id, first_ts, debit_type from debit_card
        union all
        select merchant_id, user_id, first_ts, debit_type from debit_bt
        union all
        select merchant_id, user_id, first_ts, debit_type from debit_zce
    ),
    first_debit as (
        select merchant_id, user_id, first_ts, debit_type,
               row_number() over (partition by merchant_id, user_id order by first_ts) as rn
        from all_debits
    ),
    first_debit_with_amount as (
        select fd.merchant_id, fd.user_id,
               ((fd.first_ts + interval '5' hour)::date)::text as first_debit_date,
               fd.debit_type as first_debit_type,
               case
                   when fd.debit_type = 'cn_send' then (
                       select round((dcn.amount / 1e6)::numeric, 2)
                       from digital_cash_notes dcn
                       where dcn.depositor_id = fd.user_id
                         and dcn.status = 'claimed'
                         and dcn.created_at = fd.first_ts
                       limit 1
                   )
                   when fd.debit_type = 'card' then (
                       select round((abs(t.amount) / 1e6)::numeric, 2)
                       from transactions t
                       where t.user_id = fd.user_id
                         and t.status = 3
                         and t.type = 'Transaction::CardSpend'
                         and t.posted_at = fd.first_ts
                       limit 1
                   )
                   when fd.debit_type = 'bank_transfer' then (
                       select round((abs(t.amount) / 1e6)::numeric, 2)
                       from transactions t
                       where t.user_id = fd.user_id
                         and t.status = 3
                         and t.type = 'Transaction::BankTransfer'
                         and t.posted_at = fd.first_ts
                       limit 1
                   )
                   when fd.debit_type = 'zce_order' then (
                       select round((zceo.amount / 1e6)::numeric, 2)
                       from zar_cash_exchange_orders zceo
                       where zceo.initiator_id = fd.user_id
                         and zceo.status = 'completed'
                         and zceo.created_at = fd.first_ts
                       limit 1
                   )
               end as first_debit_amount
        from first_debit fd
        where fd.rn = 1
    ),

    -- Credit source: CN received (excluding onboarding note)
    first_credit as (
        select oul.merchant_id, oul.user_id,
               min(dcn.claimed_at) as first_credit_ts
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.claimant_id = oul.user_id
            and dcn.status = 'claimed'
            and dcn.id != oul.onboarding_note_id
            and dcn.claimed_at > oul.onboarding_claimed_at
        group by 1, 2
    ),
    first_credit_with_amount as (
        select fc.merchant_id, fc.user_id,
               ((fc.first_credit_ts + interval '5' hour)::date)::text as first_credit_date,
               (
                   select round((dcn.amount / 1e6)::numeric, 2)
                   from digital_cash_notes dcn
                   where dcn.claimant_id = fc.user_id
                     and dcn.status = 'claimed'
                     and dcn.claimed_at = fc.first_credit_ts
                   limit 1
               ) as first_credit_amount
        from first_credit fc
    ),

    -- Combine: full outer join debit + credit per merchant/user
    all_users as (
        select merchant_id, user_id from first_debit_with_amount
        union
        select merchant_id, user_id from first_credit_with_amount
    )
    select au.merchant_id::text, au.user_id::text,
           d.first_debit_date,
           d.first_debit_type,
           coalesce(d.first_debit_amount, 0) as first_debit_amount,
           c.first_credit_date,
           coalesce(c.first_credit_amount, 0) as first_credit_amount
    from all_users au
    left join first_debit_with_amount d on d.merchant_id = au.merchant_id and d.user_id = au.user_id
    left join first_credit_with_amount c on c.merchant_id = au.merchant_id and c.user_id = au.user_id
    order by au.merchant_id, au.user_id
    """


def user_cycling_query() -> str:
    """One row per onboarded user: did they send a CN back to their onboarding merchant?"""
    return f"""
    with {_merchants_cte()},
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at,
               dcn.id as onboarding_note_id
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),
    cn_back_to_merchant as (
        select oul.merchant_id, oul.user_id,
               count(*) as cn_back_count,
               round((sum(dcn.amount) / 1e6)::numeric, 2) as cn_back_amount
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.depositor_id = oul.user_id
            and dcn.claimant_id = oul.merchant_id
            and dcn.status = 'claimed'
            and dcn.created_at > oul.onboarding_claimed_at
        group by 1, 2
    )
    select oul.merchant_id::text, oul.user_id::text,
           case when cbm.user_id is not null then true else false end as sent_cn_to_merchant,
           coalesce(cbm.cn_back_amount, 0) as cn_to_merchant_amount,
           coalesce(cbm.cn_back_count, 0) as cn_to_merchant_count
    from onboarded_users_list oul
    left join cn_back_to_merchant cbm
        on cbm.merchant_id = oul.merchant_id and cbm.user_id = oul.user_id
    order by oul.merchant_id, oul.user_id
    """


def rapid_onboarding_query() -> str:
    """Sybil detection: burst onboarding of fake users per merchant."""
    return f"""
    with {_merchants_cte()},
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),
    merchant_onb_counts as (
        select merchant_id,
               count(*) as total_onboarded,
               extract(epoch from max(onboarding_claimed_at) - min(onboarding_claimed_at)) as span_seconds
        from onboarded_users_list
        group by 1
        having count(*) >= 3
    ),
    hourly_windows as (
        select o1.merchant_id,
               o1.onboarding_claimed_at as window_start,
               count(*) as onboards_in_window
        from onboarded_users_list o1
        join onboarded_users_list o2
            on o1.merchant_id = o2.merchant_id
            and o2.onboarding_claimed_at >= o1.onboarding_claimed_at
            and o2.onboarding_claimed_at < o1.onboarding_claimed_at + interval '1' hour
        group by 1, 2
    ),
    max_hourly as (
        select merchant_id, max(onboards_in_window) as max_per_hour
        from hourly_windows
        group by 1
    ),
    consecutive_gaps as (
        select merchant_id,
               extract(epoch from (
                   lead(onboarding_claimed_at) over (partition by merchant_id order by onboarding_claimed_at)
                   - onboarding_claimed_at
               )) as gap_seconds
        from onboarded_users_list
    ),
    median_gaps as (
        select merchant_id,
               round(percentile_cont(0.5) within group (order by gap_seconds)::numeric, 0) as median_gap_seconds
        from consecutive_gaps
        where gap_seconds is not null
        group by 1
    )
    select mc.merchant_id::text,
           m.business_name,
           mc.total_onboarded,
           round(mc.span_seconds::numeric, 0) as span_seconds,
           coalesce(mh.max_per_hour, 0) as max_per_hour,
           coalesce(mg.median_gap_seconds, 0) as median_gap_seconds
    from merchant_onb_counts mc
    join merchants m on m.merchant_id = mc.merchant_id
    left join max_hourly mh on mh.merchant_id = mc.merchant_id
    left join median_gaps mg on mg.merchant_id = mc.merchant_id
    order by mh.max_per_hour desc nulls last, mc.total_onboarded desc
    """


def cycling_timing_query() -> str:
    """Grinding detection: timing and amount of cycling back to merchant."""
    return f"""
    with {_merchants_cte()},
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at,
               dcn.amount / 1e6 as onboarding_amount
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),
    first_cn_back as (
        select oul.merchant_id, oul.user_id,
               oul.onboarding_amount,
               min(dcn.created_at) as first_cn_back_at,
               (select round((d2.amount / 1e6)::numeric, 2)
                from digital_cash_notes d2
                where d2.depositor_id = oul.user_id
                  and d2.claimant_id = oul.merchant_id
                  and d2.status = 'claimed'
                  and d2.created_at > oul.onboarding_claimed_at
                order by d2.created_at
                limit 1
               ) as cn_back_amount,
               oul.onboarding_claimed_at
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.depositor_id = oul.user_id
            and dcn.claimant_id = oul.merchant_id
            and dcn.status = 'claimed'
            and dcn.created_at > oul.onboarding_claimed_at
        group by 1, 2, 3, oul.onboarding_claimed_at
    )
    select fcb.merchant_id::text,
           fcb.user_id::text,
           m.business_name,
           round(extract(epoch from (fcb.first_cn_back_at - fcb.onboarding_claimed_at))::numeric, 0) as seconds_to_cycle,
           round(fcb.onboarding_amount::numeric, 2) as onboarding_amount,
           coalesce(fcb.cn_back_amount, 0) as cn_back_amount,
           case when round(fcb.onboarding_amount::numeric, 2) = coalesce(fcb.cn_back_amount, 0)
                then true else false end as exact_match
    from first_cn_back fcb
    join merchants m on m.merchant_id = fcb.merchant_id
    order by seconds_to_cycle asc
    """


def merchant_self_send_ring_query() -> str:
    """Collusion/OCA detection: merchant recycles funds through onboarded users."""
    return f"""
    with {_merchants_cte()},
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at,
               dcn.id as onboarding_note_id
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),
    user_cn_back as (
        select oul.merchant_id, oul.user_id,
               dcn.created_at as cn_back_at,
               dcn.amount / 1e6 as cn_back_amount
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.depositor_id = oul.user_id
            and dcn.claimant_id = oul.merchant_id
            and dcn.status = 'claimed'
            and dcn.created_at > oul.onboarding_claimed_at
    ),
    merchant_sends_after as (
        select ucb.merchant_id, ucb.user_id as cycling_user_id,
               ucb.cn_back_at,
               oul2.user_id as next_user_id,
               oul2.onboarding_claimed_at as next_onboard_at
        from user_cn_back ucb
        join onboarded_users_list oul2
            on oul2.merchant_id = ucb.merchant_id
            and oul2.user_id != ucb.user_id
            and oul2.onboarding_claimed_at > ucb.cn_back_at
            and oul2.onboarding_claimed_at < ucb.cn_back_at + interval '1' hour
    )
    select msa.merchant_id::text,
           m.business_name,
           msa.cycling_user_id::text,
           msa.next_user_id::text,
           round(extract(epoch from (msa.next_onboard_at - msa.cn_back_at))::numeric, 0) as seconds_between,
           ((msa.cn_back_at + interval '5' hour)::date)::text as cycle_date
    from merchant_sends_after msa
    join merchants m on m.merchant_id = msa.merchant_id
    order by msa.merchant_id, msa.cn_back_at
    """


def merchant_fraud_summary_query() -> str:
    """Composite fraud risk summary per merchant — aggregates all signals."""
    return f"""
    with {_merchants_cte()},
    onboarded_users_list as (
        select dcn.depositor_id as merchant_id,
               dcn.claimant_id as user_id,
               dcn.claimed_at as onboarding_claimed_at,
               dcn.amount / 1e6 as onboarding_amount,
               dcn.id as onboarding_note_id
        from digital_cash_notes dcn
        join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
          and dcn.depositor_id in (select merchant_id from merchants)
          and dcn.claimant_id not in ({EXCLUDED_IDS_SQL})
    ),
    merchant_counts as (
        select merchant_id,
               count(*) as total_onboarded
        from onboarded_users_list
        group by 1
    ),
    cn_back as (
        select oul.merchant_id, oul.user_id,
               min(dcn.created_at) as first_cn_back_at,
               oul.onboarding_claimed_at,
               oul.onboarding_amount,
               (select round((d2.amount / 1e6)::numeric, 2)
                from digital_cash_notes d2
                where d2.depositor_id = oul.user_id
                  and d2.claimant_id = oul.merchant_id
                  and d2.status = 'claimed'
                  and d2.created_at > oul.onboarding_claimed_at
                order by d2.created_at limit 1
               ) as cn_back_amount
        from onboarded_users_list oul
        join digital_cash_notes dcn on dcn.depositor_id = oul.user_id
            and dcn.claimant_id = oul.merchant_id
            and dcn.status = 'claimed'
            and dcn.created_at > oul.onboarding_claimed_at
        group by 1, 2, oul.onboarding_claimed_at, oul.onboarding_amount
    ),
    cycling_agg as (
        select merchant_id,
               count(*) as cycled_count,
               round(avg(extract(epoch from (first_cn_back_at - onboarding_claimed_at)))::numeric, 0) as avg_seconds_to_cycle,
               count(*) filter (
                   where round(onboarding_amount::numeric, 2) = coalesce(cn_back_amount, 0)
               ) as exact_match_count
        from cn_back
        group by 1
    ),
    hourly_windows as (
        select o1.merchant_id,
               count(*) as onboards_in_window
        from onboarded_users_list o1
        join onboarded_users_list o2
            on o1.merchant_id = o2.merchant_id
            and o2.onboarding_claimed_at >= o1.onboarding_claimed_at
            and o2.onboarding_claimed_at < o1.onboarding_claimed_at + interval '1' hour
        group by o1.merchant_id, o1.onboarding_claimed_at
    ),
    max_hourly as (
        select merchant_id, max(onboards_in_window) as max_per_hour
        from hourly_windows
        group by 1
    ),
    select mc.merchant_id::text,
           m.business_name,
           mc.total_onboarded,
           coalesce(ca.cycled_count, 0) as cycled_count,
           case when mc.total_onboarded > 0
                then round((coalesce(ca.cycled_count, 0)::numeric / mc.total_onboarded) * 100, 0)
                else 0 end as pct_cycled,
           coalesce(ca.avg_seconds_to_cycle, 0) as avg_seconds_to_cycle,
           coalesce(ca.exact_match_count, 0) as exact_match_count,
           coalesce(mh.max_per_hour, 0) as max_per_hour
    from merchant_counts mc
    join merchants m on m.merchant_id = mc.merchant_id
    left join cycling_agg ca on ca.merchant_id = mc.merchant_id
    left join max_hourly mh on mh.merchant_id = mc.merchant_id
    where mc.total_onboarded >= 3
    order by coalesce(ca.cycled_count, 0) desc, mc.total_onboarded desc
    """


def merchant_retention_query() -> str:
    """Weekly active merchant pairs: merchant_id + week_start for retention analysis."""
    return """
    with all_merchants as (
        select distinct mos.merchant_id
        from merchant_onboarding_submissions mos
        where mos.status in ('active', 'pending')
          and lower(mos.business_name) not like '%test%'
          and mos.merchant_id is not null
    ),
    zce_activity as (
        select zce.fulfiller_id as merchant_id,
               date_trunc('week', (zce.completed_at + interval '5' hour)::date)::date as week_start
        from zar_cash_exchange_orders zce
        where zce.status = 'completed'
          and zce.fulfiller_id in (select merchant_id from all_merchants)
    ),
    cn_activity as (
        select dcn.depositor_id as merchant_id,
               date_trunc('week', (dcn.claimed_at + interval '5' hour)::date)::date as week_start
        from digital_cash_notes dcn
        where dcn.status = 'claimed'
          and dcn.claimed_at is not null
          and dcn.depositor_id in (select merchant_id from all_merchants)
    )
    select merchant_id::text, week_start::text
    from (
        select merchant_id, week_start from zce_activity
        union
        select merchant_id, week_start from cn_activity
    ) combined
    group by 1, 2
    order by 2, 1
    """
