# Ambassador Insights Reference

**Data sources:** Google Sheet (visit log) + PostgreSQL DB (demo + onboard verification)

---

## 1. What Is a "Demo" (DB Definition)

**Source table:** `digital_cash_notes`
**Mechanism:** Ambassador sends a digital cash note to the merchant's ZAR account.

```
got_demo  = any claimed dcn from an ambassador to that merchant (total_amount > 0)
$5 demo   = total dcn amount >= 5,000,000 atomic USDC  (5,000,000 = $5.00)
```

- Amount stored in **atomic USDC** — divide by 1,000,000 for dollars
- `dcn.depositor_id` = ambassador user ID
- `dcn.claimant_id` = merchant user ID
- Required filters: `dcn.status = 'claimed'` AND `dcn.claimed_at is not null`
- PKT date: `(dcn.claimed_at + interval '5' hour)::date`

**Sheet cross-verify:** Column `Golden Flow Amount` is the demo amount entered manually by the ambassador. Compare to `sum(dcn.amount)/1e6` from DB for the same merchant phone on the same date. Discrepancies = missed or partial demos.

---

## 2. What Is an "Onboarding" (DB Definition)

Two sources, always UNIONed — zero overlap since Dec 13 2025 (SHIP-2069):

| Source | Table | Condition |
|--------|-------|-----------|
| MOS (legacy) | `merchant_onboarding_submissions` | `status in ('active', 'pending')`, matched via phone |
| PE (new) | `product_enrollments` JOIN `product_definitions` | `pd.code = 'zar_cash_exchange_merchant'`, `pe.state = 2` |

**Sheet cross-verify:** Column `QR Setup Done` (`yes`/`true`/`done`/`1` = onboarded). DB is more reliable — sheet is self-reported.

---

## 3. Google Sheet

| Property | Value |
|----------|-------|
| Sheet ID | `1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ` |
| Tab | `Form Responses 1` |
| URL | https://docs.google.com/spreadsheets/d/1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ |

**Column reference:**

| Column Name | What It Contains |
|-------------|-----------------|
| `Timestamp` | Visit date/time (stored as UTC — add 5h for PKT) |
| `Visit Type` | `onboarding` / `new merchant` / `new` / `new onboarding` = onboarding visit |
| `Opener Outcome` | `Not Interested` = opener failed |
| `Golden Flow Amount` | Demo amount in dollars, entered by ambassador (self-reported) |
| `QR Setup Done` | `yes`/`true`/`done`/`1` = merchant onboarded (self-reported) |
| `Ambassador Name` | Raw name as typed — see name map below |
| `Merchant Phone` | Phone number (format varies — normalize to digits only for DB joins) |
| `Shop Name` | Business name |
| `Location Lat` | GPS latitude |
| `Location Lng` | GPS longitude |

**Ambassador name map (sheet → canonical):**

| Sheet Name | Canonical Name |
|-----------|---------------|
| Arslan Ansari | Arslan Ansari |
| Afsar Khan | Afsar Khan |
| Sharoon Sam93 | Sharoon Javed |
| Zahid Khan | Muhammad Zahid |
| Junaid Ahmed | Junaid Ahmed |
| irfan rana | Muhammad Irfan |
| Umer Daniyal | Umer Daniyal |
| Owais Feroz | Owais Feroz |

---

## 4. Ambassador ID → Name (DB)

| User ID | Username | Real Name |
|---------|----------|-----------|
| `019bfeae-4ab6-77ef-8fe5-7fb91c7755ce` | `user_1ef1d1ea` | Arslan Ansari |
| `019c22a1-07a6-7c67-889e-5c655fe8ae11` | `owaisferoz1` | Owais Feroz |
| `a9519a82-c510-4b5b-a24b-ecec3f68de23` | `muhammadzahid` | Muhammad Zahid |

Full ambassador list: `user_to_user_roles` JOIN `user_roles` WHERE `ur.name = 'ambassador'`.

---

## 5. Exclusion List (19 test/internal UUIDs)

Always exclude from both ambassador and merchant sides:

```
'57d456f2-84f7-4db5-b5b8-4f494f29c9dc','83845f51-170d-44b4-907b-68ba7e3a87d0',
'bf1de49f-179a-400f-b023-2e73b57a59d9','aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec','f8780ccb-3d67-46e5-baa8-0811c64c730d',
'84c74165-5eb6-4e4f-8b23-06892c09bdbc','110228ec-0e17-482e-a692-3a34bdb3ab65',
'9520d1e5-a92e-49d8-9a9e-6747523e0ed7','f32dd3b4-cad1-487b-8c87-e4924117c050',
'5fd86e56-6c6d-426f-818e-f85898ec8dbf','274bff97-2c1b-4410-a79d-dd81f33f5c15',
'1b397809-6185-4273-b098-7d86cc821bc4','44e72414-f6bc-4975-83fa-3046e28e9a94',
'a464fe4a-ed62-41ca-87f4-4ab48d3c4058','0eb006a5-53a8-41c2-9cca-6c06dc1c2549',
'0aac7e5e-ac3a-49a3-b588-6fed46ca6ade','0bc7e11b-5741-44b0-9c70-16fb5a58c2ee',
'958a4910-a20f-4a06-81d6-d458dcc3bf57'
```

---

## 6. Ready-to-Run SQL Queries

Run via **Metabase** → New Question → Native Query → Database 1.

---

### Q1: Per-Ambassador Demo + Onboarding Summary (all time)

```sql
with ambassadors as (
    select distinct uur.user_id as ambassador_id,
           coalesce(nullif(trim(concat(coalesce(u.first_name,''),' ',coalesce(u.last_name,''))), ''), u.username, 'Unknown') as ambassador_name
    from user_to_user_roles uur
    inner join user_roles ur on ur.id = uur.user_role_id
    inner join users u on u.id = uur.user_id
    where ur.name = 'ambassador'
      and uur.user_id not in (
          '57d456f2-84f7-4db5-b5b8-4f494f29c9dc','83845f51-170d-44b4-907b-68ba7e3a87d0',
          'bf1de49f-179a-400f-b023-2e73b57a59d9','aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
          'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec','f8780ccb-3d67-46e5-baa8-0811c64c730d',
          '84c74165-5eb6-4e4f-8b23-06892c09bdbc','110228ec-0e17-482e-a692-3a34bdb3ab65',
          '9520d1e5-a92e-49d8-9a9e-6747523e0ed7','f32dd3b4-cad1-487b-8c87-e4924117c050',
          '5fd86e56-6c6d-426f-818e-f85898ec8dbf','274bff97-2c1b-4410-a79d-dd81f33f5c15',
          '1b397809-6185-4273-b098-7d86cc821bc4','44e72414-f6bc-4975-83fa-3046e28e9a94',
          'a464fe4a-ed62-41ca-87f4-4ab48d3c4058','0eb006a5-53a8-41c2-9cca-6c06dc1c2549',
          '0aac7e5e-ac3a-49a3-b588-6fed46ca6ade','0bc7e11b-5741-44b0-9c70-16fb5a58c2ee',
          '958a4910-a20f-4a06-81d6-d458dcc3bf57'
      )
),
demos as (
    select dcn.depositor_id as ambassador_id,
           u.phone_number as merchant_phone,
           sum(dcn.amount) as total_amount
    from digital_cash_notes dcn
    inner join ambassadors a on a.ambassador_id = dcn.depositor_id
    inner join users u on u.id = dcn.claimant_id
    where dcn.status = 'claimed'
      and dcn.claimed_at is not null
      and dcn.claimant_id not in (
          '57d456f2-84f7-4db5-b5b8-4f494f29c9dc','83845f51-170d-44b4-907b-68ba7e3a87d0',
          'bf1de49f-179a-400f-b023-2e73b57a59d9','aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
          'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec','f8780ccb-3d67-46e5-baa8-0811c64c730d',
          '84c74165-5eb6-4e4f-8b23-06892c09bdbc','110228ec-0e17-482e-a692-3a34bdb3ab65',
          '9520d1e5-a92e-49d8-9a9e-6747523e0ed7','f32dd3b4-cad1-487b-8c87-e4924117c050',
          '5fd86e56-6c6d-426f-818e-f85898ec8dbf','274bff97-2c1b-4410-a79d-dd81f33f5c15',
          '1b397809-6185-4273-b098-7d86cc821bc4','44e72414-f6bc-4975-83fa-3046e28e9a94',
          'a464fe4a-ed62-41ca-87f4-4ab48d3c4058','0eb006a5-53a8-41c2-9cca-6c06dc1c2549',
          '0aac7e5e-ac3a-49a3-b588-6fed46ca6ade','0bc7e11b-5741-44b0-9c70-16fb5a58c2ee',
          '958a4910-a20f-4a06-81d6-d458dcc3bf57'
      )
    group by dcn.depositor_id, u.phone_number
),
onboardings as (
    select mos.onboarder_id as ambassador_id,
           u.phone_number as merchant_phone
    from merchant_onboarding_submissions mos
    inner join users u on u.phone_number = mos.phone_number
    where mos.status in ('active', 'pending')
      and u.id not in (
          '57d456f2-84f7-4db5-b5b8-4f494f29c9dc','83845f51-170d-44b4-907b-68ba7e3a87d0',
          'bf1de49f-179a-400f-b023-2e73b57a59d9','aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
          'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec','f8780ccb-3d67-46e5-baa8-0811c64c730d',
          '84c74165-5eb6-4e4f-8b23-06892c09bdbc','110228ec-0e17-482e-a692-3a34bdb3ab65',
          '9520d1e5-a92e-49d8-9a9e-6747523e0ed7','f32dd3b4-cad1-487b-8c87-e4924117c050',
          '5fd86e56-6c6d-426f-818e-f85898ec8dbf','274bff97-2c1b-4410-a79d-dd81f33f5c15',
          '1b397809-6185-4273-b098-7d86cc821bc4','44e72414-f6bc-4975-83fa-3046e28e9a94',
          'a464fe4a-ed62-41ca-87f4-4ab48d3c4058','0eb006a5-53a8-41c2-9cca-6c06dc1c2549',
          '0aac7e5e-ac3a-49a3-b588-6fed46ca6ade','0bc7e11b-5741-44b0-9c70-16fb5a58c2ee',
          '958a4910-a20f-4a06-81d6-d458dcc3bf57'
      )
    -- Note: PE onboardings (post Dec 13) have no onboarder_id — excluded here by design
)
select a.ambassador_name,
       count(distinct d.merchant_phone)                                                    as total_demos,
       count(distinct case when d.total_amount >= 5000000 then d.merchant_phone end)       as full_5_demos,
       count(distinct o.merchant_phone)                                                    as onboardings_as_onboarder
from ambassadors a
left join demos d on d.ambassador_id = a.ambassador_id
left join onboardings o on o.ambassador_id = a.ambassador_id
group by 1
order by 2 desc;
```

---

### Q2: Per-Ambassador Daily Activity (date range)

Change `'2026-02-10'` to your desired start date.

```sql
with ambassadors as (
    select distinct uur.user_id as ambassador_id,
           coalesce(nullif(trim(concat(coalesce(u.first_name,''),' ',coalesce(u.last_name,''))), ''), u.username) as ambassador_name
    from user_to_user_roles uur
    inner join user_roles ur on ur.id = uur.user_role_id
    inner join users u on u.id = uur.user_id
    where ur.name = 'ambassador'
      and uur.user_id not in (
          '57d456f2-84f7-4db5-b5b8-4f494f29c9dc','83845f51-170d-44b4-907b-68ba7e3a87d0',
          'bf1de49f-179a-400f-b023-2e73b57a59d9','aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
          'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec','f8780ccb-3d67-46e5-baa8-0811c64c730d',
          '84c74165-5eb6-4e4f-8b23-06892c09bdbc','110228ec-0e17-482e-a692-3a34bdb3ab65',
          '9520d1e5-a92e-49d8-9a9e-6747523e0ed7','f32dd3b4-cad1-487b-8c87-e4924117c050',
          '5fd86e56-6c6d-426f-818e-f85898ec8dbf','274bff97-2c1b-4410-a79d-dd81f33f5c15',
          '1b397809-6185-4273-b098-7d86cc821bc4','44e72414-f6bc-4975-83fa-3046e28e9a94',
          'a464fe4a-ed62-41ca-87f4-4ab48d3c4058','0eb006a5-53a8-41c2-9cca-6c06dc1c2549',
          '0aac7e5e-ac3a-49a3-b588-6fed46ca6ade','0bc7e11b-5741-44b0-9c70-16fb5a58c2ee',
          '958a4910-a20f-4a06-81d6-d458dcc3bf57'
      )
)
select a.ambassador_name,
       (dcn.claimed_at + interval '5' hour)::date as demo_date,
       count(distinct dcn.claimant_id)             as merchants_demoed,
       count(*)                                    as demo_notes_sent,
       sum(dcn.amount) / 1e6                       as total_demo_usd
from digital_cash_notes dcn
inner join ambassadors a on a.ambassador_id = dcn.depositor_id
where dcn.status = 'claimed'
  and dcn.claimed_at is not null
  and (dcn.claimed_at + interval '5' hour)::date >= '2026-02-10'
  and dcn.claimant_id not in (
      '57d456f2-84f7-4db5-b5b8-4f494f29c9dc','83845f51-170d-44b4-907b-68ba7e3a87d0',
      'bf1de49f-179a-400f-b023-2e73b57a59d9','aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
      'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec','f8780ccb-3d67-46e5-baa8-0811c64c730d',
      '84c74165-5eb6-4e4f-8b23-06892c09bdbc','110228ec-0e17-482e-a692-3a34bdb3ab65',
      '9520d1e5-a92e-49d8-9a9e-6747523e0ed7','f32dd3b4-cad1-487b-8c87-e4924117c050',
      '5fd86e56-6c6d-426f-818e-f85898ec8dbf','274bff97-2c1b-4410-a79d-dd81f33f5c15',
      '1b397809-6185-4273-b098-7d86cc821bc4','44e72414-f6bc-4975-83fa-3046e28e9a94',
      'a464fe4a-ed62-41ca-87f4-4ab48d3c4058','0eb006a5-53a8-41c2-9cca-6c06dc1c2549',
      '0aac7e5e-ac3a-49a3-b588-6fed46ca6ade','0bc7e11b-5741-44b0-9c70-16fb5a58c2ee',
      '958a4910-a20f-4a06-81d6-d458dcc3bf57'
  )
group by 1, 2
order by 2 desc, 3 desc;
```

---

### Q3: Full Demo History for a Specific Merchant Phone

Replace `'+923XXXXXXXXX'` with the target phone number (format: `+923XXXXXXXXX`).

```sql
with ambassadors as (
    select distinct uur.user_id as ambassador_id,
           coalesce(nullif(trim(concat(coalesce(u.first_name,''),' ',coalesce(u.last_name,''))), ''), u.username) as ambassador_name
    from user_to_user_roles uur
    inner join user_roles ur on ur.id = uur.user_role_id
    inner join users u on u.id = uur.user_id
    where ur.name = 'ambassador'
      and uur.user_id not in (
          '57d456f2-84f7-4db5-b5b8-4f494f29c9dc','83845f51-170d-44b4-907b-68ba7e3a87d0',
          'bf1de49f-179a-400f-b023-2e73b57a59d9','aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
          'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec','f8780ccb-3d67-46e5-baa8-0811c64c730d',
          '84c74165-5eb6-4e4f-8b23-06892c09bdbc','110228ec-0e17-482e-a692-3a34bdb3ab65',
          '9520d1e5-a92e-49d8-9a9e-6747523e0ed7','f32dd3b4-cad1-487b-8c87-e4924117c050',
          '5fd86e56-6c6d-426f-818e-f85898ec8dbf','274bff97-2c1b-4410-a79d-dd81f33f5c15',
          '1b397809-6185-4273-b098-7d86cc821bc4','44e72414-f6bc-4975-83fa-3046e28e9a94',
          'a464fe4a-ed62-41ca-87f4-4ab48d3c4058','0eb006a5-53a8-41c2-9cca-6c06dc1c2549',
          '0aac7e5e-ac3a-49a3-b588-6fed46ca6ade','0bc7e11b-5741-44b0-9c70-16fb5a58c2ee',
          '958a4910-a20f-4a06-81d6-d458dcc3bf57'
      )
)
select a.ambassador_name,
       (dcn.claimed_at + interval '5' hour)::date as demo_date,
       dcn.amount / 1e6                            as demo_usd,
       dcn.amount                                  as demo_atomic_usdc,
       dcn.id                                      as note_id
from digital_cash_notes dcn
inner join ambassadors a on a.ambassador_id = dcn.depositor_id
inner join users u on u.id = dcn.claimant_id
where dcn.status = 'claimed'
  and u.phone_number = '+923XXXXXXXXX'   -- ← replace this
order by demo_date asc;
```

---

### Q4: Revisit Count — Last 7 Days

A "revisit" = ambassador sent a demo note to a merchant on a date AFTER that merchant's first-ever demo date.

```sql
with ambassadors as (
    select distinct uur.user_id as ambassador_id
    from user_to_user_roles uur
    inner join user_roles ur on ur.id = uur.user_role_id
    where ur.name = 'ambassador'
      and uur.user_id not in (
          '57d456f2-84f7-4db5-b5b8-4f494f29c9dc','83845f51-170d-44b4-907b-68ba7e3a87d0',
          'bf1de49f-179a-400f-b023-2e73b57a59d9','aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
          'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec','f8780ccb-3d67-46e5-baa8-0811c64c730d',
          '84c74165-5eb6-4e4f-8b23-06892c09bdbc','110228ec-0e17-482e-a692-3a34bdb3ab65',
          '9520d1e5-a92e-49d8-9a9e-6747523e0ed7','f32dd3b4-cad1-487b-8c87-e4924117c050',
          '5fd86e56-6c6d-426f-818e-f85898ec8dbf','274bff97-2c1b-4410-a79d-dd81f33f5c15',
          '1b397809-6185-4273-b098-7d86cc821bc4','44e72414-f6bc-4975-83fa-3046e28e9a94',
          'a464fe4a-ed62-41ca-87f4-4ab48d3c4058','0eb006a5-53a8-41c2-9cca-6c06dc1c2549',
          '0aac7e5e-ac3a-49a3-b588-6fed46ca6ade','0bc7e11b-5741-44b0-9c70-16fb5a58c2ee',
          '958a4910-a20f-4a06-81d6-d458dcc3bf57'
      )
),
all_demo_dates as (
    select u.phone_number,
           (dcn.claimed_at + interval '5' hour)::date as demo_date
    from digital_cash_notes dcn
    inner join ambassadors a on a.ambassador_id = dcn.depositor_id
    inner join users u on u.id = dcn.claimant_id
    where dcn.status = 'claimed'
      and dcn.claimed_at is not null
      and dcn.claimant_id not in (
          '57d456f2-84f7-4db5-b5b8-4f494f29c9dc','83845f51-170d-44b4-907b-68ba7e3a87d0',
          'bf1de49f-179a-400f-b023-2e73b57a59d9','aa46304d-8e5c-4e97-8ff0-c0906813ecf4',
          'c1cc564b-dbc4-44f8-bfda-d9f85bd278ec','f8780ccb-3d67-46e5-baa8-0811c64c730d',
          '84c74165-5eb6-4e4f-8b23-06892c09bdbc','110228ec-0e17-482e-a692-3a34bdb3ab65',
          '9520d1e5-a92e-49d8-9a9e-6747523e0ed7','f32dd3b4-cad1-487b-8c87-e4924117c050',
          '5fd86e56-6c6d-426f-818e-f85898ec8dbf','274bff97-2c1b-4410-a79d-dd81f33f5c15',
          '1b397809-6185-4273-b098-7d86cc821bc4','44e72414-f6bc-4975-83fa-3046e28e9a94',
          'a464fe4a-ed62-41ca-87f4-4ab48d3c4058','0eb006a5-53a8-41c2-9cca-6c06dc1c2549',
          '0aac7e5e-ac3a-49a3-b588-6fed46ca6ade','0bc7e11b-5741-44b0-9c70-16fb5a58c2ee',
          '958a4910-a20f-4a06-81d6-d458dcc3bf57'
      )
),
first_demo as (
    select phone_number, min(demo_date) as first_demo_date
    from all_demo_dates
    group by phone_number
),
revisits_last_7 as (
    select distinct add.phone_number, add.demo_date
    from all_demo_dates add
    inner join first_demo fd on add.phone_number = fd.phone_number
    where add.demo_date > fd.first_demo_date
      and add.demo_date >= current_date - interval '6 days'
)
select count(distinct phone_number) as merchants_revisited,
       count(*)                     as revisit_visit_days,
       min(demo_date)               as earliest_revisit,
       max(demo_date)               as latest_revisit
from revisits_last_7;
```

---

## 7. Schema Nuances

| Nuance | Detail |
|--------|--------|
| **Atomic USDC** | All amounts in DB stored as atomic USDC. Divide by 1,000,000 for dollars. `5,000,000 = $5.00` |
| **PKT time offset** | DB stores UTC. Add `interval '5' hour` before casting to date |
| **Two onboarding sources** | Pre Dec 13: `merchant_onboarding_submissions` (MOS). Post Dec 13 (SHIP-2069): `product_enrollments` (PE). Always UNION both — zero overlap |
| **PE onboarder unknown** | `product_enrollments` has no `onboarder_id`. Cannot attribute PE onboardings to a specific ambassador via DB alone — use sheet `QR Setup Done` + `Ambassador Name` for attribution |
| **min() on UUID** | PostgreSQL does NOT support `min()` on UUID columns. Cast first: `min(col::text)::uuid` |
| **Phone normalization** | Sheet phones vary in format. Normalize to digits-only for DB joins: `regexp_replace(phone, '[^0-9]', '', 'g')` |
| **dcn.claimant_id ≠ always a merchant** | Cash note claimants are not necessarily merchants. Verify merchant status separately via MOS/PE if needed |
| **demo_dollars_cte in lib/sql.py** | Only covers notes to same-day-created users, from Feb 1 onwards. For all-time demo history, write a custom CTE without those filters (as in Q1–Q4 above) |

---

## 8. Key Definitions

| Term | Definition |
|------|-----------|
| **Demo** | Ambassador sent a claimed `digital_cash_note` to a merchant |
| **$5 demo** | `dcn.amount >= 5,000,000` atomic USDC on a single visit day |
| **Conversion** | Merchant ever onboarded (MOS active/pending OR PE state=2) |
| **Visit day** | One calendar date in PKT on which at least one demo note was sent |
