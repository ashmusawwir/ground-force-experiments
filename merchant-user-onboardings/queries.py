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


def _merchants_cte() -> str:
    """Shared merchants CTE used by all query functions.

    UNIONs legacy merchant_onboarding_submissions (MOS) with new
    product_enrollments (PE) merchants. Since SHIP-2069 (Dec 13),
    new merchants use PE instead of MOS. 25 merchants exist in both;
    MOS takes priority (richer metadata), PE adds only net-new.
    """
    return f"""mos_merchants as (
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
    ), pe_merchants as (
        select pe.user_id as merchant_id,
               null::text as business_name,
               null::text as city,
               null::float8 as latitude,
               null::float8 as longitude,
               'pe_enrolled' as status,
               (pe.created_at + interval '5' hour)::date as onboarding_date,
               null::text as onboarder_username,
               'Unknown' as onboarder_name
        from product_enrollments pe
        inner join product_definitions pd on pd.id = pe.product_definition_id
        where pd.code = 'zar_cash_exchange_merchant'
          and pe.state = 2
          and pe.user_id not in ({EXCLUDED_IDS_SQL})
          and pe.user_id not in (select merchant_id from mos_merchants)
    ), merchants as (
        select * from mos_merchants
        union all
        select * from pe_merchants
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
        select distinct merchant_id from (
            select mos.merchant_id
            from merchant_onboarding_submissions mos
            where mos.status in ('active', 'pending')
              and lower(mos.business_name) not like '%test%'
              and mos.merchant_id is not null
            union
            select pe.user_id as merchant_id
            from product_enrollments pe
            inner join product_definitions pd on pd.id = pe.product_definition_id
            where pd.code = 'zar_cash_exchange_merchant'
              and pe.state = 2
        ) combined
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


def cohort_analysis_query() -> str:
    """Monthly cohort retention matrix: merchants grouped by onboarding month,
    tracked across activity months with onboarding + transaction metrics.

    Single `merchants` CTE unifies MOS + PE (SHIP-2069). Transaction exclusion
    list differs from dimension exclusion — a9519a82 is excluded from transactions
    but not from the cohort dimension.
    """
    return f"""
    with merchants as (
        -- MOS merchants
        select case when mos.city = 'Sindh' then 'Karachi'
                    when mos.city = 'Punjab' then 'Lahore'
                    else mos.city end as city,
            u.id as merchant_id,
            mos.business_name,
            u.phone_number as merchant_phone_number,
            concat(u.first_name, ' ', u.last_name) as merchant_name,
            date_trunc('month', mos.created_at) as onboarding_month,
            mos.status
        from merchant_onboarding_submissions mos
        left join users u on u.phone_number = mos.phone_number
        where u.id not in ({EXCLUDED_IDS_SQL})

        union all

        -- PE merchants (net-new only, since SHIP-2069 Dec 13)
        select null::text as city,
            pe.user_id as merchant_id,
            null::text as business_name,
            u.phone_number as merchant_phone_number,
            concat(u.first_name, ' ', u.last_name) as merchant_name,
            date_trunc('month', pe.created_at) as onboarding_month,
            'active' as status
        from product_enrollments pe
        inner join product_definitions pd on pd.id = pe.product_definition_id
        inner join users u on u.id = pe.user_id
        where pd.code = 'zar_cash_exchange_merchant'
          and pe.state = 2
          and pe.user_id not in ({EXCLUDED_IDS_SQL})
          and pe.user_id not in (
              select u2.id from merchant_onboarding_submissions mos2
              inner join users u2 on u2.phone_number = mos2.phone_number
          )
    ),

    merchant_onboarding as (
        select date_trunc('month', dcn.created_at) as month,
            m.merchant_id,
            sum(dcn.amount / 1e6) as onboarding_dollars_used,
            count(*) as users_onboarded_cash_hack_merchant,
            count(case when uc.phone_number is not null
                       then uc.phone_number else null end) as secure_users_cash_hack_merchant
        from digital_cash_notes dcn
        inner join merchants m on m.merchant_id = dcn.depositor_id
        inner join users uc on uc.id = dcn.claimant_id
        inner join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.created_at >= timestamp '2025-12-01 00:00:00'
          and dcn.status = 'claimed'
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
        group by 1, 2
    ),

    transactions as (
        select date_trunc('month', zceo.created_at) as month,
            m.merchant_id,
            count(distinct zceo.initiator_id) as distinct_customers,
            count(zceo.id) as total_orders,
            sum(zceo.amount / 1e6) as dollars_sold
        from zar_cash_exchange_orders zceo
        inner join merchants m on m.merchant_id = zceo.fulfiller_id
            and m.status = 'active'
        where zceo.status = 'completed'
          and zceo.type = 'ZarCashExchange::MerchantOrder'
          and zceo.fulfiller_id not in ({COHORT_TXN_EXCLUDED_IDS_SQL})
          and zceo.initiator_id not in ({COHORT_TXN_EXCLUDED_IDS_SQL})
        group by 1, 2
    ),

    unified_metrics as (
        select month,
            merchant_id,
            merchant_id as onboarding_merchant_id,
            onboarding_dollars_used,
            users_onboarded_cash_hack_merchant,
            secure_users_cash_hack_merchant,
            null as transacting_merchant_id,
            null as dollars_sold,
            null as distinct_customers,
            null as total_orders
        from merchant_onboarding

        union all

        select month,
            merchant_id,
            null as onboarding_merchant_id,
            null as onboarding_dollars_used,
            null as users_onboarded_cash_hack_merchant,
            null as secure_users_cash_hack_merchant,
            merchant_id as transacting_merchant_id,
            dollars_sold,
            distinct_customers,
            total_orders
        from transactions
    ),

    merchant_cohort_counts as (
        select onboarding_month,
            count(distinct merchant_id) as merchants_onboarded
        from merchants
        group by onboarding_month
    )

    select m.onboarding_month,
        um.month,
        extract(year from age(um.month, m.onboarding_month)) * 12
            + extract(month from age(um.month, m.onboarding_month)) as age_in_months,
        mcc.merchants_onboarded,
        count(distinct um.merchant_id) as active_merchants,
        count(distinct um.transacting_merchant_id) as transacting_merchants,
        sum(um.distinct_customers) as distinct_customers,
        sum(um.total_orders) as total_orders,
        sum(um.dollars_sold) as dollars_sold,
        count(distinct um.onboarding_merchant_id) as onboarding_merchants,
        sum(um.onboarding_dollars_used) as onboarding_dollars_used,
        sum(um.users_onboarded_cash_hack_merchant) as users_onboarded_cash_hack_merchant,
        sum(um.secure_users_cash_hack_merchant) as secure_users_cash_hack_merchant
    from merchants m
    left join unified_metrics um on um.merchant_id = m.merchant_id
    left join merchant_cohort_counts mcc on mcc.onboarding_month = m.onboarding_month
    group by 1, 2, 3, 4
    having coalesce(um.month, m.onboarding_month) < date_trunc('month', now())
    order by 1, 3
    """


def monthly_metrics_query() -> str:
    """Monthly metrics dashboard — standalone query for Metabase.

    Simplified from the original inline query:
    - Single `merchants` CTE (MOS + PE) replaces repeated mos+users joins
    - EXCLUDED_IDS used everywhere (original had 1 ID in trader_metrics,
      14 unique in merchant_user_transactions, same list 3× in merchant_onboarding)
    - Fixed bug: zceo_t join filter was referencing zceo_m alias
    - PE merchants included in merchant_onboarding + merchant_onboarding_users
    """
    return f"""
    with months as (
        select distinct date_trunc('month', date) as month
        from (select generate_series(date '2025-10-01', current_date, interval '1 day')::date as date) g
    ),

    merchants as (
        -- MOS merchants (active only)
        select u.id as merchant_id,
               date_trunc('month', mos.created_at) as onboarding_month
        from merchant_onboarding_submissions mos
        inner join users u on u.phone_number = mos.phone_number
        where mos.status = 'active'
          and u.id not in ({EXCLUDED_IDS_SQL})

        union all

        -- PE merchants (net-new since SHIP-2069)
        select pe.user_id as merchant_id,
               date_trunc('month', pe.created_at) as onboarding_month
        from product_enrollments pe
        inner join product_definitions pd on pd.id = pe.product_definition_id
        where pd.code = 'zar_cash_exchange_merchant'
          and pe.state = 2
          and pe.user_id not in ({EXCLUDED_IDS_SQL})
          and pe.user_id not in (
              select u2.id from merchant_onboarding_submissions mos2
              inner join users u2 on u2.phone_number = mos2.phone_number
              where mos2.status = 'active'
          )
    ),

    trader_metrics as (
        select date_trunc('month', created_at) as month,
            sum(zceo.amount / 1e6) as dollars_purchased_from_trader,
            percentile_cont(0.5) within group (order by extract(epoch from (completed_at - activated_at)) / 60) as median_fulfilment_minutes,
            percentile_cont(0.5) within group (order by amount / 1e6) as median_transaction_value_trader
        from zar_cash_exchange_orders zceo
        where type = 'ZarCashExchange::TraderOrder'
          and status = 'completed'
          and created_at > date '2025-10-01'
          and zceo.initiator_id not in ({EXCLUDED_IDS_SQL})
        group by 1
    ),

    merchant_user_transactions as (
        select date_trunc('month', zceo.created_at) as month,
            count(zceo.id) as merchant_user_transactions,
            count(distinct initiator_id) as distinct_users,
            count(distinct fulfiller_id) as distinct_merchants,
            sum(zceo.amount / 1e6) as dollars_purchased_from_merchants,
            percentile_cont(0.5) within group (order by zceo.amount / 1e6) as median_transaction_value_merchant
        from zar_cash_exchange_orders zceo
        inner join users u on u.id = zceo.initiator_id
        where zceo.type = 'ZarCashExchange::MerchantOrder'
          and zceo.status = 'completed'
          and zceo.created_at > date '2025-10-01'
          and zceo.initiator_id not in ({EXCLUDED_IDS_SQL})
        group by 1
    ),

    merchant_onboarding as (
        select m.onboarding_month,
            m.merchant_id,
            date(min(zceo_t.completed_at)) as first_trader_transaction_month,
            date(min(zceo_m.completed_at)) as first_customer_transaction_month
        from merchants m
        left join zar_cash_exchange_orders zceo_m on zceo_m.fulfiller_id = m.merchant_id
            and zceo_m.type = 'ZarCashExchange::MerchantOrder'
            and zceo_m.status = 'completed'
            and zceo_m.initiator_id not in ({EXCLUDED_IDS_SQL})
        left join zar_cash_exchange_orders zceo_t on zceo_t.initiator_id = m.merchant_id
            and zceo_t.type = 'ZarCashExchange::TraderOrder'
            and zceo_t.status = 'completed'
        group by 1, 2
    ),

    onboarded_merchant_stats as (
        select d.month,
            count(mo.merchant_id) filter (where mo.onboarding_month = d.month) as merchants_onboarded,
            count(mo.merchant_id) filter (where first_trader_transaction_month = d.month or first_customer_transaction_month = d.month) as merchants_with_first_transaction,
            count(mo.merchant_id) filter (where mo.onboarding_month::date <= d.month
                  and (least(mo.first_trader_transaction_month, mo.first_customer_transaction_month) is null
                     or least(mo.first_trader_transaction_month, mo.first_customer_transaction_month)::date > d.month)) as merchants_with_no_transactions,
            count(distinct mo.merchant_id) filter (where mo.onboarding_month = d.month and first_customer_transaction_month is not null) as merchants_onboarded_and_user_activated,
            count(distinct mo.merchant_id) filter (where mo.onboarding_month = d.month and first_trader_transaction_month is not null) as merchants_onboarded_and_trader_activated,
            sum((first_customer_transaction_month::date - onboarding_month::date)) filter (where mo.onboarding_month = d.month) as days_to_first_customer_transaction,
            sum((first_trader_transaction_month::date - onboarding_month::date)) filter (where mo.onboarding_month = d.month) as days_to_first_trader_transaction
        from months d
        left join merchant_onboarding mo on mo.onboarding_month <= d.month
        group by 1
    ),

    users_date as (
        select date_trunc('month', created_at) as month,
            max(initial_queue_position) as waitlist,
            count(*) as accounts_created
        from users u
        where u.created_at >= date_trunc('month', date '2025-10-01')
        group by 1
    ),

    graduations as (
        select date_trunc('month', created_at) as month,
            sum(number_of_users) as users_graduated
        from bulk_graduations
        group by 1
    ),

    wallets as (
        select date_trunc('month', created_at) as month,
            count(*) as wallets_created
        from wallets_base_wallets wbw
        where wbw.created_at >= date_trunc('month', date '2025-10-01')
          and wbw.type = 'Wallets::SquadsMultisig'
        group by 1
    ),

    cards as (
        select date_trunc('month', created_at) as month,
            count(distinct user_id) as cards_created
        from cards_debit_cards cbc
        group by 1
    ),

    cash_note_hack as (
        select date_trunc('month', dcn.created_at) as month,
            count(distinct uc.id) as users_onboarded_cash_note,
            count(case when uc.phone_number is not null then uc.phone_number else null end) as secure_users_cash_hack,
            percentile_cont(0.5) within group (order by dcn.amount / 1e6) as median_cash_note,
            count(case when dcn.amount / 1e6 > 0.01 then dcn.id else null end) as cash_notes_greater_than_penny
        from digital_cash_notes dcn
        inner join users u on u.id = dcn.depositor_id
        inner join users uc on uc.id = dcn.claimant_id
        inner join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
        group by 1
    ),

    cash_notes_raw as (
        select date_trunc('month', dcn.created_at) as month,
            sum(amount / 1e6) as wallet_spend,
            count(distinct depositor_id) as wallet_users,
            count(id) as wallet_transactions
        from digital_cash_notes dcn
        where status = 'claimed'
        group by 1

        union all

        select date_trunc('month', t.created_at) as month,
            sum(amount / 1e6) as wallet_spend,
            count(distinct t.user_id) as wallet_users,
            count(t.id) as wallet_transactions
        from transactions t
        where type in ('Transaction::DigitalCashTransfer', 'Transaction::TokenTransfer')
          and direction = '0'
          and status = '3'
          and t.created_at < date '2025-12-11'
        group by 1
    ),

    cash_notes as (
        select month,
            sum(wallet_spend) as wallet_spend,
            sum(wallet_users) as wallet_users,
            sum(wallet_transactions) as wallet_transactions
        from cash_notes_raw
        group by 1
    ),

    card_transactions as (
        select date_trunc('month', t.created_at) as month,
            sum(amount / 1e6) as card_spend,
            count(distinct t.user_id) as card_users,
            count(t.id) as card_transactions
        from transactions t
        where status = '3'
          and type = 'Transaction::CardSpend'
        group by 1
    ),

    merchant_onboarding_users as (
        select date_trunc('month', dcn.created_at) as month,
            count(*) as users_onboarded_cash_hack_merchant,
            count(case when uc.phone_number is not null then uc.phone_number else null end) as secure_users_cash_hack_merchant,
            percentile_cont(0.5) within group (order by dcn.amount / 1e6) as median_cash_note_merchant,
            count(case when dcn.amount / 1e6 > 0.01 then dcn.id else null end) as cash_notes_greater_than_penny_merchant,
            count(distinct dcn.depositor_id) as unique_merchants
        from digital_cash_notes dcn
        inner join merchants m on m.merchant_id = dcn.depositor_id
        inner join users uc on uc.id = dcn.claimant_id
        inner join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.created_at >= timestamp '2025-12-01 00:00:00'
          and dcn.status = 'claimed'
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
        group by 1
    )

    select
        d.month::date as month,
        -- trader metrics
        tm.dollars_purchased_from_trader,
        tm.median_fulfilment_minutes,
        tm.median_transaction_value_trader,
        -- merchant order metrics
        mut.merchant_user_transactions,
        mut.distinct_users,
        mut.distinct_merchants,
        mut.dollars_purchased_from_merchants,
        mut.median_transaction_value_merchant,
        -- merchant onboarding stats
        oms.merchants_onboarded,
        oms.merchants_with_first_transaction,
        oms.merchants_with_no_transactions,
        oms.merchants_onboarded_and_user_activated,
        oms.merchants_onboarded_and_trader_activated,
        oms.days_to_first_customer_transaction,
        oms.days_to_first_trader_transaction,
        -- users
        ud.waitlist,
        ud.accounts_created,
        -- graduations
        g.users_graduated,
        -- wallets / cards
        w.wallets_created,
        c.cards_created,
        -- cash note onboardings (all depositors)
        cnh.users_onboarded_cash_note,
        cnh.secure_users_cash_hack,
        cnh.median_cash_note,
        cnh.cash_notes_greater_than_penny,
        -- wallet transactions
        cn.wallet_spend,
        cn.wallet_users,
        cn.wallet_transactions,
        -- card transactions
        ct.card_spend,
        ct.card_users,
        ct.card_transactions,
        -- cash note onboardings (by merchants only)
        mou.users_onboarded_cash_hack_merchant,
        mou.secure_users_cash_hack_merchant,
        mou.median_cash_note_merchant,
        mou.cash_notes_greater_than_penny_merchant,
        mou.unique_merchants
    from months d
    left join trader_metrics tm using (month)
    left join merchant_user_transactions mut using (month)
    left join onboarded_merchant_stats oms using (month)
    left join users_date ud using (month)
    left join graduations g using (month)
    left join wallets w using (month)
    left join cards c using (month)
    left join cash_note_hack cnh using (month)
    left join cash_notes cn using (month)
    left join card_transactions ct using (month)
    left join merchant_onboarding_users mou using (month)
    order by d.month
    """


def daily_merchant_activity_query() -> str:
    """Daily merchant operations dashboard — per-merchant, per-day activity with dimension fields.

    Simplified from original inline Metabase query:
    - Single `merchants` CTE (MOS + PE) replaces 6 repeated mos+users joins
    - EXCLUDED_IDS used consistently (original had 15 IDs in merchant_user,
      18 in dimension, none elsewhere)
    - PE merchants included in all CTEs and dimension
    - `merchant_creation` simplified to select from merchants CTE
    - Removed unused `users ua` join in merchant_user CTE
    """
    return f"""
    with dates as (
        select generate_series(date '2025-12-01', current_date, interval '1 day')::date as date
    ),

    merchants as (
        -- MOS merchants (active only)
        select u.id as merchant_id,
               date(mos.created_at + interval '5' hour) as onboarding_date
        from merchant_onboarding_submissions mos
        inner join users u on u.phone_number = mos.phone_number
        where mos.status = 'active'
          and u.id not in ({EXCLUDED_IDS_SQL})

        union all

        -- PE merchants (net-new since SHIP-2069)
        select pe.user_id as merchant_id,
               date(pe.created_at + interval '5' hour) as onboarding_date
        from product_enrollments pe
        inner join product_definitions pd on pd.id = pe.product_definition_id
        where pd.code = 'zar_cash_exchange_merchant'
          and pe.state = 2
          and pe.user_id not in ({EXCLUDED_IDS_SQL})
          and pe.user_id not in (
              select u2.id from merchant_onboarding_submissions mos2
              inner join users u2 on u2.phone_number = mos2.phone_number
              where mos2.status = 'active'
          )
    ),

    merchant_user as (
        select date(zceo.created_at + interval '5' hour) as date,
            zceo.fulfiller_id as merchant_id,
            count(distinct uu.phone_number) as transaction_users,
            count(zceo.id) as user_orders,
            sum(zceo.amount / 1e6) as dollars_sold
        from zar_cash_exchange_orders zceo
        inner join merchants m on m.merchant_id = zceo.fulfiller_id
        inner join users uu on uu.id = zceo.initiator_id
        where zceo.status = 'completed'
          and zceo.type = 'ZarCashExchange::MerchantOrder'
          and zceo.initiator_id not in ({EXCLUDED_IDS_SQL})
        group by 1, 2
    ),

    merchant_trader as (
        select date(zceo.created_at + interval '5' hour) as date,
            zceo.initiator_id as merchant_id,
            count(zceo.id) as trader_orders,
            sum(zceo.amount / 1e6) as dollars_bought
        from zar_cash_exchange_orders zceo
        where zceo.status = 'completed'
          and zceo.type = 'ZarCashExchange::TraderOrder'
        group by 1, 2
    ),

    merchant_onboarding as (
        select date(dcn.created_at + interval '5' hour) as date,
            m.merchant_id,
            sum(dcn.amount / 1e6) as dollars_used,
            count(*) as users_onboarded_cash_hack_merchant,
            count(case when uc.phone_number is not null then uc.phone_number else null end) as secure_users_cash_hack_merchant
        from digital_cash_notes dcn
        inner join merchants m on m.merchant_id = dcn.depositor_id
        inner join users uc on uc.id = dcn.claimant_id
        inner join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.created_at >= timestamp '2025-12-01 00:00:00'
          and dcn.status = 'claimed'
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
        group by 1, 2
    ),

    onboarded_users as (
        select dcn.claimant_id as user_id,
            m.merchant_id as onboarding_merchant_id,
            dcn.id as onboarding_note_id,
            dcn.claimed_at as onboarding_time
        from digital_cash_notes dcn
        inner join merchants m on m.merchant_id = dcn.depositor_id
        inner join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
    ),

    user_merchant_transactions as (
        select dcn.claimant_id as user_id,
            m.merchant_id,
            dcn.claimed_at as txn_time,
            dcn.id as txn_id,
            'cash_note' as txn_type
        from digital_cash_notes dcn
        inner join merchants m on m.merchant_id = dcn.depositor_id
        where dcn.status = 'claimed'

        union all

        select zceo.initiator_id as user_id,
            zceo.fulfiller_id as merchant_id,
            zceo.created_at as txn_time,
            zceo.id as txn_id,
            'order' as txn_type
        from zar_cash_exchange_orders zceo
        inner join merchants m on m.merchant_id = zceo.fulfiller_id
        where zceo.status = 'completed'
          and zceo.type = 'ZarCashExchange::MerchantOrder'
    ),

    user_second_txn as (
        select ou.user_id,
            ou.onboarding_merchant_id as merchant_id,
            umt.txn_time,
            umt.txn_id,
            row_number() over (partition by ou.user_id, ou.onboarding_merchant_id order by umt.txn_time) as txn_rank
        from onboarded_users ou
        inner join user_merchant_transactions umt
            on umt.user_id = ou.user_id
            and umt.merchant_id = ou.onboarding_merchant_id
            and umt.txn_id != ou.onboarding_note_id
            and umt.txn_time > ou.onboarding_time
    ),

    merchant_activations as (
        select date(txn_time + interval '5' hour) as date,
            merchant_id,
            count(*) as user_activations
        from user_second_txn
        where txn_rank = 1
        group by 1, 2
    ),

    merchant_dimension as (
        select case when mos.city = 'Sindh' then 'Karachi' else mos.city end as city,
            mos.business_name,
            u.phone_number as merchant_phone_number,
            concat(u.first_name, ' ', u.last_name) as merchant_name,
            m.merchant_id,
            m.onboarding_date,
            concat(ua.first_name, ' ', ua.last_name) as onboarder_name,
            ua.phone_number as onboarder_phone_number,
            mos.address,
            mos.longitude as longitude_,
            mos.latitude as latitude_,
            wbw.address as wallet_address
        from merchants m
        inner join users u on u.id = m.merchant_id
        left join merchant_onboarding_submissions mos on mos.phone_number = u.phone_number
        left join users ua on ua.id = mos.onboarder_id
        left join wallets_base_wallets wbw on wbw.user_id = m.merchant_id
            and wbw.type = 'Wallets::SquadsMultisig'
            and wbw.address <> 'BgcN59YVPgjpy4Av89NgoB9qgkLrS67pUery7ce7j185'
    ),

    unions as (
        select date, merchant_id,
            transaction_users, user_orders, dollars_sold,
            null::bigint as trader_orders, null::numeric as dollars_bought,
            null::bigint as users_onboarded_cash_hack_merchant,
            null::bigint as secure_users_cash_hack_merchant,
            null::bigint as user_activations
        from merchant_user

        union all

        select date, merchant_id,
            null, null, null,
            trader_orders, dollars_bought,
            null, null, null
        from merchant_trader

        union all

        select date, merchant_id,
            null, null, null,
            null, null,
            users_onboarded_cash_hack_merchant, secure_users_cash_hack_merchant,
            null
        from merchant_onboarding

        union all

        select onboarding_date as date, merchant_id,
            null, null, null,
            null, null,
            null, null, null
        from merchants

        union all

        select date, merchant_id,
            null, null, null,
            null, null,
            null, null,
            user_activations
        from merchant_activations
    )

    select md.city,
        md.business_name,
        md.merchant_name,
        md.merchant_phone_number,
        md.onboarding_date,
        md.onboarder_name,
        md.onboarder_phone_number,
        md.address,
        md.longitude_,
        md.latitude_,
        md.wallet_address,
        d.date,
        sum(u.transaction_users) as transaction_users,
        sum(u.user_orders) as user_orders,
        sum(u.dollars_sold) as dollars_sold,
        sum(u.trader_orders) as trader_orders,
        sum(u.dollars_bought) as dollars_bought,
        sum(u.users_onboarded_cash_hack_merchant) as users_onboarded_cash_hack_merchant,
        sum(u.secure_users_cash_hack_merchant) as secure_users_cash_hack_merchant,
        sum(u.user_activations) as user_activations
    from dates d
    inner join unions u on d.date = u.date
    inner join merchant_dimension md on md.merchant_id = u.merchant_id
    group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
    order by md.merchant_phone_number, d.date
    """


def daily_overview_query() -> str:
    """Daily overview dashboard — all key metrics at daily granularity for Metabase.

    Simplified from the original inline query:
    - Single `merchants` CTE (MOS + PE) replaces mos+users joins in merchant_onboarding
      and merchant_onboarding_users
    - EXCLUDED_IDS used everywhere (original had 14 IDs in merchant_user_transactions,
      same 14 repeated 2x in merchant_onboarding with zceo_t bug, none in trader_metrics)
    - Fixed bug: zceo_t join filter was referencing zceo_m.initiator_id
    - PE merchants included in merchant_onboarding + merchant_onboarding_users
    """
    return f"""
    with dates as (
        select generate_series(date '2025-10-01', current_date, interval '1 day')::date as date
    ),

    merchants as (
        -- MOS merchants (active only)
        select u.id as merchant_id,
               date(mos.created_at) as onboarding_date
        from merchant_onboarding_submissions mos
        inner join users u on u.phone_number = mos.phone_number
        where mos.status = 'active'
          and u.id not in ({EXCLUDED_IDS_SQL})

        union all

        -- PE merchants (net-new since SHIP-2069)
        select pe.user_id as merchant_id,
               date(pe.created_at) as onboarding_date
        from product_enrollments pe
        inner join product_definitions pd on pd.id = pe.product_definition_id
        where pd.code = 'zar_cash_exchange_merchant'
          and pe.state = 2
          and pe.user_id not in ({EXCLUDED_IDS_SQL})
          and pe.user_id not in (
              select u2.id from merchant_onboarding_submissions mos2
              inner join users u2 on u2.phone_number = mos2.phone_number
              where mos2.status = 'active'
          )
    ),

    trader_metrics as (
        select date(created_at) as date,
            sum(zceo.amount / 1e6) as dollars_purchased_from_trader,
            percentile_cont(0.5) within group (order by extract(epoch from (completed_at - activated_at)) / 60) as median_fulfilment_minutes,
            percentile_cont(0.5) within group (order by amount / 1e6) as median_transaction_value_trader
        from zar_cash_exchange_orders zceo
        where type = 'ZarCashExchange::TraderOrder'
          and status = 'completed'
          and created_at > date '2025-10-01'
          and zceo.initiator_id not in ({EXCLUDED_IDS_SQL})
        group by 1
    ),

    merchant_user_transactions as (
        select date(zceo.created_at) as date,
            count(zceo.id) as merchant_user_transactions,
            count(distinct initiator_id) as distinct_users,
            count(distinct fulfiller_id) as distinct_merchants,
            sum(zceo.amount / 1e6) as dollars_purchased_from_merchants,
            percentile_cont(0.5) within group (order by zceo.amount / 1e6) as median_transaction_value_user
        from zar_cash_exchange_orders zceo
        inner join users u on u.id = zceo.initiator_id
        where zceo.type = 'ZarCashExchange::MerchantOrder'
          and zceo.status = 'completed'
          and zceo.created_at > date '2025-10-01'
          and zceo.initiator_id not in ({EXCLUDED_IDS_SQL})
        group by 1
    ),

    merchant_onboarding as (
        select m.onboarding_date,
            m.merchant_id,
            date(min(zceo_t.completed_at)) as first_trader_transaction_date,
            date(min(zceo_m.completed_at)) as first_customer_transaction_date
        from merchants m
        left join zar_cash_exchange_orders zceo_m on zceo_m.fulfiller_id = m.merchant_id
            and zceo_m.type = 'ZarCashExchange::MerchantOrder'
            and zceo_m.status = 'completed'
            and zceo_m.initiator_id not in ({EXCLUDED_IDS_SQL})
        left join zar_cash_exchange_orders zceo_t on zceo_t.initiator_id = m.merchant_id
            and zceo_t.type = 'ZarCashExchange::TraderOrder'
            and zceo_t.status = 'completed'
        group by 1, 2
    ),

    onboarded_merchant_stats as (
        select d.date,
            count(mo.merchant_id) filter (where mo.onboarding_date = d.date) as merchants_onboarded,
            count(mo.merchant_id) filter (where first_trader_transaction_date = d.date or first_customer_transaction_date = d.date) as merchants_with_first_transaction,
            count(mo.merchant_id) filter (where mo.onboarding_date::date <= d.date
                  and (least(mo.first_trader_transaction_date, mo.first_customer_transaction_date) is null
                     or least(mo.first_trader_transaction_date, mo.first_customer_transaction_date)::date > d.date)) as merchants_with_no_transactions,
            count(distinct mo.merchant_id) filter (where mo.onboarding_date = d.date and first_customer_transaction_date is not null) as merchants_onboarded_and_user_activated,
            count(distinct mo.merchant_id) filter (where mo.onboarding_date = d.date and first_trader_transaction_date is not null) as merchants_onboarded_and_trader_activated,
            sum((first_customer_transaction_date::date - onboarding_date::date)) filter (where mo.onboarding_date = d.date) as days_to_first_customer_transaction,
            sum((first_trader_transaction_date::date - onboarding_date::date)) filter (where mo.onboarding_date = d.date) as days_to_first_trader_transaction
        from dates d
        left join merchant_onboarding mo on mo.onboarding_date <= d.date
        group by 1
    ),

    users_date as (
        select date(u.created_at) as date,
            max(initial_queue_position) as waitlist,
            count(*) as accounts_created
        from users u
        where u.created_at >= date_trunc('month', date '2025-10-01')
        group by 1
    ),

    graduations as (
        select date(created_at) as date,
            sum(number_of_users) as users_graduated
        from bulk_graduations
        group by 1
    ),

    wallets as (
        select date(wbw.created_at) as date,
            count(*) as wallets_created
        from wallets_base_wallets wbw
        where wbw.created_at >= date_trunc('month', date '2025-10-01')
          and wbw.type = 'Wallets::SquadsMultisig'
        group by 1
    ),

    cards as (
        select date(cbc.created_at) as date,
            count(distinct user_id) as cards_created
        from cards_debit_cards cbc
        group by 1
    ),

    cash_note_hack as (
        select date(dcn.created_at) as date,
            count(distinct uc.id) as users_onboarded_cash_note,
            count(case when uc.phone_number is not null then uc.phone_number else null end) as secure_users_cash_hack,
            percentile_cont(0.5) within group (order by dcn.amount / 1e6) as median_cash_note,
            count(case when dcn.amount / 1e6 > 0.01 then dcn.id else null end) as cash_notes_greater_than_penny
        from digital_cash_notes dcn
        inner join users u on u.id = dcn.depositor_id
        inner join users uc on uc.id = dcn.claimant_id
        inner join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.status = 'claimed'
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
        group by 1
    ),

    cash_notes_raw as (
        select date(dcn.created_at) as date,
            sum(amount / 1e6) as wallet_spend,
            count(distinct depositor_id) as wallet_users,
            count(id) as wallet_transactions
        from digital_cash_notes dcn
        where status = 'claimed'
        group by 1

        union all

        select date(t.created_at) as date,
            sum(amount / 1e6) as wallet_spend,
            count(distinct t.user_id) as wallet_users,
            count(t.id) as wallet_transactions
        from transactions t
        where type in ('Transaction::DigitalCashTransfer', 'Transaction::TokenTransfer')
          and direction = '0'
          and status = '3'
          and t.created_at < date '2025-12-11'
        group by 1
    ),

    cash_notes as (
        select date,
            sum(wallet_spend) as wallet_spend,
            sum(wallet_users) as wallet_users,
            sum(wallet_transactions) as wallet_transactions
        from cash_notes_raw
        group by 1
    ),

    card_transactions as (
        select date(t.created_at) as date,
            sum(amount / 1e6) as card_spend,
            count(distinct t.user_id) as card_users,
            count(t.id) as card_transactions
        from transactions t
        where status = '3'
          and type = 'Transaction::CardSpend'
        group by 1
    ),

    merchant_onboarding_users as (
        select date(dcn.created_at + interval '5' hour) as date,
            count(*) as users_onboarded_cash_hack_merchant,
            count(case when uc.phone_number is not null then uc.phone_number else null end) as secure_users_cash_hack_merchant,
            percentile_cont(0.5) within group (order by dcn.amount / 1e6) as median_cash_note_merchant,
            count(case when dcn.amount / 1e6 > 0.01 then dcn.id else null end) as cash_notes_greater_than_penny_merchant,
            count(distinct dcn.depositor_id) as unique_merchants
        from digital_cash_notes dcn
        inner join merchants m on m.merchant_id = dcn.depositor_id
        inner join users uc on uc.id = dcn.claimant_id
        inner join wallets_base_wallets wbw on wbw.user_id = dcn.claimant_id
            and wbw.type = 'Wallets::SquadsMultisig'
        where dcn.created_at >= timestamp '2025-12-01 00:00:00'
          and dcn.status = 'claimed'
          and abs(extract(epoch from (wbw.created_at - dcn.claimed_at))) < 120
        group by 1
    )

    select *
    from dates d
    left join trader_metrics tm using (date)
    left join merchant_user_transactions mut using (date)
    left join onboarded_merchant_stats oms using (date)
    left join users_date ud using (date)
    left join graduations g using (date)
    left join wallets w using (date)
    left join cards c using (date)
    left join cash_note_hack cnh using (date)
    left join cash_notes cn using (date)
    left join card_transactions ct using (date)
    left join merchant_onboarding_users using (date)
    order by 1
    """
