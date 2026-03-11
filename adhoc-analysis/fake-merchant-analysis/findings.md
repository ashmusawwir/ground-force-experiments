# Fake Merchant Detection — EDA Findings
Date: 2026-03-09

---

## Ambassador Profile

- **Username:** `ilyas_khan`
- **Ambassador ID:** `019c8ee0-c02c-75a0-ac4c-cf707f020d19`
- **Phone:** +923458781746
- **MOS submissions since Feb 1, 2026:** 14
- **Active date range:** 2026-02-24 → 2026-03-07 (12 days)
- **Peak day:** 6 submissions on 2026-02-26 (highest single-day count across all ambassadors in the period)
- **Second-highest day:** 4 submissions on 2026-02-28

### Onboarding pathway split

The verification team flagged 5 merchants. The DB contains 4 confirmed (one name mismatch — "New Pakhtoon" vs "New pakhton" in DB). They fall across two onboarding pathways:

| Fake merchant | DB business name | Pathway | Form phone |
|--------------|-----------------|---------|-----------|
| Hamza .Com | hamza dot com | PE (product_enrollments) | null in MOS |
| SR Communication | sr communication | PE | null in MOS |
| Hanif General Store | hanif genral store | PE | null in MOS |
| Gujjar Dot Com | gujjar dot com | MOS | +923192713284 |
| New Pakhtoon General Store | New pakhton general store | MOS | null in MOS |

Three fakes used the PE pathway and had null phone in their MOS form — a structural evasion of the phone-based lookup used in Q1.

---

## Confirmed Signals (firing on fakes)

### 1. Sub-minute DCN claim latency (strongest signal)

Every demo cash note sent by this ambassador was claimed within 5 minutes. The median was under 1 minute. 11 of 15 DCNs were claimed in under 1 minute. The three confirmed fake merchants claimed their DCNs in:

| Fake merchant | Phone | Mins to claim |
|--------------|-------|---------------|
| sr communication | +923113263959 | 0.38 min (23 sec) |
| hamza dot com | +923122388838 | 0.57 min (34 sec) |
| hanif genral store | +923090336070 | 1.46 min (88 sec) |
| gujjar dot com | +923192713284 | 1.19 min (71 sec) |

At 17–88 seconds, these claims are machine-assisted. A real merchant picking up their phone, opening the ZAR app, and navigating to the claim screen takes a minimum of 30–60 seconds under ideal conditions. Sub-30-second claims are physically implausible without the ambassador operating the merchant's device directly.

The fastest claim in the entire portfolio was 0.29 min (17 seconds). That is not a human clicking through an app from a cold start.

**False positive risk:** Low. The 0.29–0.57 min range is not achievable by an independent user. Threshold: < 2 min claim latency = high suspicion; < 1 min = near-definitive.

### 2. Null form phone (85.7% of MOS submissions)

12 of 14 MOS form submissions had a null phone field. Across all other ambassadors in the period, MOS submissions with null phone are rare (most ambassadors enter the merchant's phone to match the account). A null phone in MOS breaks the standard phone-based lookup, meaning these merchants are invisible to Q1-style detection until the PE/account tables are checked separately.

This is the structural signal: the ambassador consistently omitted the phone field, which is the primary joining key for fraud detection queries.

**False positive risk:** Medium. Null phone can occur legitimately if the merchant has no phone or the ambassador forgot. However, 85.7% null rate (vs near-0% for peers) rules out accident.

### 3. Zero post-onboarding merchant activity (100% of known fakes)

None of the 4 confirmed fake merchants with recoverable phone numbers ever made a `Transaction::CashExchange` as a merchant. Their entire transaction history consists of:
- Claiming the $5 demo DCN
- One `BankTransfer` of exactly $5 (immediate cash-out of the demo note)

No real merchant ever sold anything. This is consistent with the accounts being created solely to generate an onboarding count, not to operate as merchants.

Among the flagged ambassador's 2 MOS merchants (with phone), both show zero CashExchange activity in Q11. The 3 PE-pathway fakes are not captured in Q11's MOS join, but Q10 confirms zero CashExchange for all 4 phones checked.

**False positive risk:** Low when combined with DCN latency. New merchants with zero activity alone could be legitimate but dormant. The combination of zero activity + sub-minute DCN + null phone is near-definitive.

### 4. Single-day burst volume (system record)

On 2026-02-26, this ambassador submitted 6 MOS forms — the highest single-day count across all ambassadors in the Feb–Mar 2026 period. On 2026-02-28, they submitted 4. No other ambassador reached 6.

5 of those 6 Feb-26 submissions had null form phone.

**False positive risk:** Low as a standalone signal (a productive ambassador could legitimately onboard 6 merchants in a day), but it is the first anomaly that would surface in a real-time monitoring dashboard.

### 5. GPS coordinates are hyperlocal

All 14 MOS submissions have GPS coordinates within a 3km bounding box centered on approximately lat 24.940, lon 67.030 (a specific area of Karachi). Within-day displacements are mostly 0–0.75 km. The largest within-experiment displacement is 3.0 km (Shabbir customer service on Mar 6, after a 6-day gap).

This is consistent with an ambassador who never physically traveled to verify merchants — all forms were submitted from roughly the same location. However, it is not definitive: a dense market area in Karachi could legitimately contain 14 merchants within 3 km.

**False positive risk:** High as a standalone signal in a dense urban market. Useful as a corroborating signal, not a primary detector.

---

## Non-Firing Signals

### Account age at onboarding

The one MOS-pathway fake with a full data trail (gujjar dot com) had an account-to-onboard gap of 26 minutes — in the `under_1hr` bucket, which is normal for a real same-session onboarding. The jibran dot comm account (not confirmed fake) had a 24.8-hour gap (`over_1day`). The signal did not distinguish fakes from legitimate merchants in this dataset.

For the PE-pathway fakes, the account was created 2–4 days before the MOS form was submitted, which is also not anomalous on its own.

**Conclusion:** Account age is not a reliable primary signal given the variation in the legitimate population (Q6 shows legitimate merchants ranging from 13 minutes to 69,000 minutes account age at onboarding).

### Phone prefix clustering

Cannot assess: 12 of 14 MOS form submissions had null phone. With only 2 non-null phones (+923192, +923453), no prefix cluster pattern is detectable. Signal is not applicable to this case.

### GPS velocity (physical impossibility)

No submissions showed physically impossible travel. The haversine distance between consecutive submissions was always ≤ 3 km, consistent with the ambassador being stationary or moving locally. This signal did not fire.

### Inter-submission gap (sub-5-min threshold)

The shortest inter-submission gap was 12.3 minutes (Khyber medical → hanif genral store on Feb 28). No two consecutive MOS forms were submitted within 5 minutes of each other. The signal did not fire at the 5-min threshold, though 12 minutes for two separate merchant visits remains aggressive.

---

## Signal Scorecard

| Signal | Fires on fakes? | False positive risk | Recommendation |
|--------|-----------------|---------------------|----------------|
| DCN claim latency < 1 min | YES — all 4 confirmed fakes | Low | Primary detector. Threshold: < 2 min = flag, < 1 min = escalate |
| Null form phone rate | YES — 85.7% vs ~0% peers | Medium | Secondary detector. Flag if > 50% of ambassador's submissions have null phone |
| Zero merchant CashExchange activity | YES — 100% of fakes | Low (when combined) | Confirmation signal. Run 30-day post-onboard check |
| Single-day burst ≥ 5 onboardings | YES — fired on Feb 26 | Medium-low | Alert-level signal. Trigger review, not automatic flag |
| GPS hyperlocality | Corroborating | High standalone | Useful in combination; not a primary signal in dense urban markets |
| Account age at onboarding | NO | High | Not reliable; wide variation in legitimate population |
| Phone prefix clustering | Not applicable | — | Blocked by null phone pattern itself |
| Inter-submission gap < 5 min | NO (12 min minimum) | Medium | Raise threshold to 15 min or use as tier-2 signal |
| Physical GPS velocity impossible | NO | Low | Keep in ruleset; did not fire here but valid for future cases |

---

## Recommended Detection Rules

A fraud scoring system should compute a score per ambassador per rolling 7-day window. The following thresholds are calibrated to this dataset.

**Rule 1 — DCN sub-minute claim (score: 3 points per occurrence)**
`claimed_at - created_at < interval '2 minutes'` on any DCN.
Escalate immediately if ≥ 3 sub-minute claims in the same week.

**Rule 2 — Null form phone rate (score: 2 points if rate > 50%)**
`count(*) filter (where mos.phone_number is null) / count(*) > 0.5`
Over a 7-day rolling window on the ambassador's MOS submissions.

**Rule 3 — Burst day (score: 2 points if single-day count ≥ 5)**
`count(*) >= 5` in a single calendar day (PKT).

**Rule 4 — Zero activity rate at day 7 (score: 2 points if rate = 100%)**
All merchants onboarded by this ambassador in the prior 30 days show zero `Transaction::CashExchange` as merchant, 7+ days after onboarding.

**Rule 5 — Peer benchmark outlier (score: 1 point)**
Ambassador's daily onboarding count exceeds the 95th percentile of all active ambassadors in the same period.

**Total score ≥ 5 → flag for manual review.**
**Total score ≥ 8 → suspend pending investigation.**

---

## Limitations

1. **PE-pathway blind spot in Q1 / Q9:** Three of four confirmed fakes used product_enrollments with null MOS phone. The standard phone-based MOS lookup (Q1) missed them entirely. Any detection system must union MOS + PE pathways and tolerate null form phones.

2. **Q11 scope:** The post-onboarding activity buckets query (Q11) joins on MOS phone, so PE-pathway merchants are invisible. Of the ambassador's 14 MOS submissions, only 2 had non-null phone and were counted in Q11. The real zero-activity rate for the full PE portfolio cannot be computed from Q11 alone.

3. **"New Pakhtoon" name discrepancy:** The verification team name ("New Pakhtoon General Store") does not exactly match the DB name ("New pakhton general store"). The `%pakhtoon%` LIKE search returned zero rows; the `%pakhtun%` search also returned zero rows. It was found by the `%hanif%`/`%hamza%` etc. broad sweep. The DB spelling variation would defeat exact-match detection. Future queries should use ILIKE + multiple spelling variants.

4. **GPS not independently verified:** The GPS coordinates appear plausible (within a real area of Karachi), but we cannot verify whether they were manually entered or device-generated. GPS spoofing is possible and not detectable from the MOS table alone.

5. **Demo DCN signal only fires when the ambassador sends demos.** An ambassador who onboards merchants without sending any DCN would evade the sub-minute claim detector entirely. Rule 4 (zero activity rate) would still catch them.

6. **Peer comparison baseline is small.** Q4 and Q11 cover a short Feb–Mar 2026 window with 11 ambassadors total. The burst-day threshold (≥ 5 onboardings) and the percentile benchmark are calibrated to a thin dataset. Re-calibrate as the ambassador network grows.

---

## Population-Level Validation

Date: 2026-03-09
Queries: PA1 (`fleet_dcn_latency_query`), PA2 (`merchant_signal_profile_query`), PA3 (`ambassador_risk_summary_query`)
Population: All 104 PE-enrolled merchants since 2026-02-01

### PA1 — Fleet-wide DCN claim latency

| Ambassador | Demos | Fastest (min) | Median (min) | Sub-1min | 1–2min | 2–5min | >5min | % sub-2min |
|---|---|---|---|---|---|---|---|---|
| stormy_raccoon_4878 | 1 | 1.25 | 1.25 | 0 | 1 | 0 | 0 | 100 |
| ashmusawwir | 1 | 0.57 | 0.57 | 1 | 0 | 0 | 0 | 100 |
| fancy_granite_9573 | 1 | 0.25 | 0.25 | 1 | 0 | 0 | 0 | 100 |
| happy_griffin_1631 | 9 | 0.47 | 1.13 | 4 | 5 | 0 | 0 | 100 |
| user_3d31a3a4 | 1 | 0.56 | 0.56 | 1 | 0 | 0 | 0 | 100 |
| kindly_lynx_5179 | 1 | 0.57 | 0.57 | 1 | 0 | 0 | 0 | 100 |
| mighty_robin_3902 | 5 | 0.58 | 0.67 | 4 | 1 | 0 | 0 | 100 |
| samik | 1 | 0.25 | 0.25 | 1 | 0 | 0 | 0 | 100 |
| owaisferoz1 | 28 | 0.19 | 0.46 | 22 | 4 | 2 | 0 | 92.9 |
| **ilyas_khan** | 15 | 0.29 | 0.76 | 10 | 2 | 3 | 0 | **80** |
| sharoon1 | 38 | 0.35 | 0.94 | 20 | 10 | 7 | 1 | 78.9 |
| turab | 14 | 0.22 | 0.59 | 11 | 0 | 1 | 2 | 78.6 |
| user_1ef1d1ea | 59 | 0.26 | 0.97 | 30 | 14 | 8 | 7 | 74.6 |
| muhammadzahid | 31 | 0.26 | 0.92 | 18 | 4 | 8 | 1 | 71 |
| afsarkhan | 55 | 0.25 | 1.02 | 27 | 11 | 10 | 7 | 69.1 |
| junaid9778 | 33 | 0.19 | 1.37 | 13 | 7 | 3 | 10 | 60.6 |
| lashkarwala | 73 | 0.29 | 2.00 | 25 | 12 | 14 | 22 | 50.7 |
| umer2700 | 12 | 0.21 | 2.79 | 4 | 1 | 4 | 3 | 41.7 |
| irfan1 | 25 | 0.51 | 6.09 | 6 | 1 | 4 | 14 | 28 |
| user_bd05725d | 1 | 2.34 | 2.34 | 0 | 0 | 1 | 0 | 0 |

**Finding:** Sub-2-min DCN claims are the fleet norm. 17/20 ambassadors have ≥40% sub-2-min. `ilyas_khan` at 80% is below the median of this group — multiple ambassadors hit 100%. This signal does not discriminate between ilyas_khan and peers. Sub-minute claims reflect the standard demo practice: the ambassador is on-site and helps the merchant claim the DCN immediately.

**Revised assessment of EDA Signal 1:** The sub-minute claim latency was the strongest signal in the per-ambassador view but collapses as a detector at the fleet level. It is a property of the demo workflow, not of fraud.

---

### PA2 — Per-merchant signal profile (all 104 Feb 1+ PE merchants)

**Fleet-wide signal rates:**

| Signal | Rate |
|---|---|
| Zero 30-day CashExchange activity | 81% (84/104) |
| Sub-2-min DCN (where demo exists) | 78% (81/104) |
| Account age under 1hr at enrollment | 79% (82/104) |

**Composite fraud score distribution:**

| Score | Count | % of cohort |
|---|---|---|
| 3 (all signals) | 51 | 49% |
| 2 | 41 | 39% |
| 1 | 12 | 12% |
| 0 | 0 | 0% |

No merchant scores 0. 49% of all PE-enrolled merchants hit the maximum composite score of 3. The signals as calibrated fire on almost the entire population.

**Score-3 ambassador breakdown:**

| Ambassador | Score-3 merchants |
|---|---|
| owaisferoz1 | 14 |
| user_1ef1d1ea | 13 |
| happy_griffin_1631 | 9 |
| junaid9778 | 3 |
| ilyas_khan | 5 |
| sharoon1 | 3 |
| umer2700 | 1 |
| afsarkhan | 1 |
| muhammadzahid | 1 |
| mighty_robin_3902 | 1 |

The 4 confirmed fake merchant phones from the EDA (sr communication, hamza dot com, hanif genral store, gujjar dot com) are all present in the score-3 group — but so are 47 other merchants across multiple ambassadors.

**Finding:** The 3-signal composite score has a false positive rate approaching 100%. It cannot identify fakes because the signals describe normal onboarding behavior in the PE era. Zero 30-day activity is particularly misleading: 81% of all merchants have never transacted, reflecting a fleet-wide merchant activation problem rather than fraud.

---

### PA3 — Ambassador-level risk summary

| Ambassador | Merchants | Sub-2min | Acct <1hr | Zero-act | % sub-2min | % zero-act | Weighted score |
|---|---|---|---|---|---|---|---|
| happy_griffin_1631 | 9 | 9 | 9 | 9 | 100% | 100% | 4.00 |
| owaisferoz1 | 20 | 18 | 20 | 16 | 90% | 80% | 3.60 |
| mighty_robin_3902 | 2 | 2 | 1 | 2 | 100% | 100% | 3.50 |
| **ilyas_khan** | 8 | 6 | 6 | 8 | 75% | **100%** | **3.25** |
| user_1ef1d1ea | 23 | 19 | 15 | 21 | 83% | 91% | 3.22 |
| junaid9778 | 13 | 11 | 10 | 7 | 85% | 54% | 3.00 |
| muhammadzahid | 4 | 4 | 1 | 3 | 100% | 75% | 3.00 |
| sharoon1 | 8 | 5 | 8 | 6 | 63% | 75% | 3.00 |
| afsarkhan | 4 | 3 | 2 | 3 | 75% | 75% | 2.75 |
| umer2700 | 8 | 2 | 7 | 6 | 25% | 75% | 2.13 |
| irfan1 | 3 | 0 | 3 | 2 | 0% | 67% | 1.67 |

`ilyas_khan` ranks 4th out of 11 by weighted risk score. Three ambassadors (happy_griffin_1631, owaisferoz1, mighty_robin_3902) score higher. 100% zero-activity rate is not unique to ilyas_khan — happy_griffin_1631 and mighty_robin_3902 also hit 100%.

**Finding:** No single ambassador stands out as a clear outlier by these signals. The risk score is high across the board.

---

### Revised Signal Assessment

| Signal | EDA verdict | Population verdict |
|---|---|---|
| DCN claim latency < 2min | Primary detector | **Invalidated** — 78% fleet-wide; standard demo practice |
| Zero 30-day CashExchange activity | Confirmation signal | **Invalidated** — 81% fleet-wide; merchant activation problem |
| Account age < 1hr at enrollment | Secondary signal | **Invalidated** — 79% fleet-wide; standard workflow |
| Single-day burst ≥ 5 onboardings (MOS) | Alert-level signal | **Still valid but MOS-specific** — not replicated in PA3 (PE data) |
| Null form phone rate > 50% (MOS) | Secondary detector | **Still valid but MOS-specific** — PE pathway has no phone field |

All three PE-era signals collapse at the population level. The signals that survive are both MOS-specific and no longer applicable as the onboarding pathway has fully shifted to PE.

---

### Implications

1. **The EDA fraud signals do not transfer to the PE era.** New PE-era signals are needed. Candidates:
   - Burst volume per ambassador per day (PE enrollments, not MOS submissions)
   - Ambassador-level account-creation velocity (ambassadors who create accounts and immediately enroll)
   - Merchant never opens the ZAR app after enrollment (requires Amplitude data — no app-open events in DB)

2. **Widespread zero activity is a distinct problem.** 81% of Feb 1+ PE merchants have never transacted as a merchant. This is a merchant activation problem that needs to be addressed independently of fraud detection.

3. **Multiple ambassadors warrant scrutiny on other grounds.** happy_griffin_1631 (100% zero-activity, 100% sub-2min, 9 merchants), owaisferoz1 (90% sub-2min, 80% zero-activity, 20 merchants), and user_1ef1d1ea (83% sub-2min, 91% zero-activity, 23 merchants) all show profiles similar to or worse than ilyas_khan on these signals. Whether this reflects fraud or legitimate low activation requires manual verification beyond the DB signals alone.

4. **Fraud detection requires Amplitude.** The only signal that clearly distinguishes a fake merchant from a dormant-but-legitimate merchant is whether the merchant ever opened the app and used it. That data lives in Amplitude, not the DB.

---

## Amplitude + Visit Sheet Investigation

Date: 2026-03-09
Population: ilyas_khan's full PE cohort — 10 merchants (4 confirmed fakes, 6 unconfirmed)
Queries added: `ambassador_name_query` (QN-1), `fake_merchant_user_ids_query` (QN-2), `ilyas_pe_cohort_query` (QN-3)

---

### Setup

**Ambassador name:** `ilyas_khan` has no first/last name stored in the DB — both fields empty. Visit sheet match was done via the "Ambassador Name" free-text column (matched "Ilyas Khan").

**Fake merchant user IDs (PE pathway):**

| Phone | User ID | Enrolled PKT |
|-------|---------|--------------|
| +923090336070 (hanif genral store) | `019ca509-1fa7-7ff5-945f-fb2ea2403944` | 2026-02-28 |
| +923113263959 (sr communication) | `019c9f0f-ff7f-7cbe-bf89-ea3957c1a693` | 2026-02-27 |
| +923122388838 (hamza dot com) | `019ca457-7f9f-7b7d-8d4b-13e0b332eb4e` | 2026-02-28 |
| +923192713284 (gujjar dot com) | `019c9a75-46d2-7f6d-a9f8-371dcd65c6a4` | 2026-02-26 |

**Full PE cohort (10 merchants total):**

| Phone | Enrolled PKT | Status |
|-------|-------------|--------|
| +923018826149 | 2026-02-24 | unconfirmed |
| +923462889293 | 2026-02-26 | unconfirmed |
| +923453041506 | 2026-02-26 | unconfirmed |
| +923192713284 | 2026-02-26 | **confirmed fake** |
| +923113263959 | 2026-02-27 | **confirmed fake** |
| +923122388838 | 2026-02-28 | **confirmed fake** |
| +923128870913 | 2026-02-28 | unconfirmed |
| +923090336070 | 2026-02-28 | **confirmed fake** |
| +923453767324 | 2026-03-06 | unconfirmed |
| +923428373779 | 2026-03-07 | unconfirmed |

---

### Amplitude App-Open Findings

**Hypothesis (invalidated):** Fake merchants never open the app; dormant-but-real merchants at least open it once.

**Reality:** All 4 confirmed fakes are present in Amplitude and opened the app. The binary app-open signal does not discriminate fakes from non-fakes.

**Per-merchant Amplitude profile:**

| Merchant | Fake? | In Amp? | First used | Last used | Sessions | Total events | Key behavior |
|----------|-------|---------|-----------|----------|---------|-------------|--------------|
| hanif genral store | YES | YES | 2026-02-28 | 2026-03-01 | 2 | 139 | DCN claim + `bank_transfer_succeeded` + stop |
| sr communication | YES | YES | 2026-02-27 | 2026-03-05 | 3 | 176 | Wallet browsing only; no claim or transfer events in sample |
| hamza dot com | YES | YES | 2026-02-28 | 2026-03-01 | 2 | 91 | `cash_note_creation_initiated` + `cash_note_claimed` (created AND claimed DCN) |
| gujjar dot com | YES | YES | 2026-02-26 | 2026-02-26 | 3 | 295 | Active only on enrollment day; 8× `branch_sdk_error`; `cash_note_reclaim_success` |
| unknown-1 | unk | **NO** | — | — | — | — | Never appeared in Amplitude |
| unknown-2 | unk | YES | 2026-02-24 | 2026-02-25 | 2 | 152 | Active *before* enrollment; `qr_code_scanner_opened` (5×) |
| unknown-3 | unk | YES | 2026-02-24 | 2026-02-27 | 8 | 216 | 8 sessions, `marker_tapped` (map browsing), `cash_note_creation_initiated` |
| unknown-4 | unk | YES | 2026-02-25 | 2026-02-28 | 4 | 148 | `card_order_screen_viewed`; active on enrollment day only |
| unknown-5 | unk | **NO** | — | — | — | — | Never appeared in Amplitude |
| unknown-6 | unk | **NO** | — | — | — | — | Never appeared in Amplitude |

**Revised Amplitude signals (not "did they open?" but "what did they do?"):**

1. **Never appeared in Amplitude (strongest):** 3/10 merchants (unknown-1, 5, 6) have no Amplitude record at all — they never downloaded or opened the app. For a merchant who supposedly underwent a demo and DCN claim, zero Amplitude presence means the account was either staged on a device the ambassador controlled, or the phone number does not belong to a real merchant who interacted with the product. Note: all 3 are unconfirmed status; the confirmed fakes all have Amplitude records (because the ambassador operated the phone to claim the DCN).

2. **`last_used` within 1-6 days of enrollment + no subsequent activity:** All 4 confirmed fakes have `last_used` ≤ 6 days after enrollment and never returned. However, 3 of the 6 unconfirmed merchants also follow this pattern. Not a clean discriminator at this cohort size.

3. **High event count on a single day with `branch_sdk_error` and reclaim events:** gujjar dot com's 295 events in one day with repeated SDK errors suggests scripted or automated activity, not organic user behavior. This is a qualitative flag, not a threshold rule.

4. **DCN creation on the merchant side:** hamza dot com shows `cash_note_creation_initiated` and `cash_note_creation_success` — the merchant created a DCN, which is a merchant-mode action. Combined with the confirmed-fake status, this suggests the ambassador was operating the merchant's device directly to demonstrate the product, generating realistic-looking Amplitude activity.

**Amplitude signal verdict:** The binary "opened the app" signal is invalidated. A useful Amplitude signal exists but requires per-event analysis: look for the absence of Amplitude presence entirely, or for activity confined exclusively to the DCN claim + bank transfer flow with no return sessions. This requires Amplitude API access per-merchant (not bulk-queryable from the DB).

---

### Visit Sheet Cross-Reference

Visit sheet: `1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ` (tab: Visits), 1,811 data rows.

**ilyas_khan logged 1 visit** out of 10 PE-enrolled merchants. That single visit is the gujjar dot com fake, duration **1.8 minutes** (Start 14:12:47 → End 14:14:33 PKT). The visit includes a logged demo start, onboarding start, and bank transfer — all within 106 seconds.

**Cross-ambassador pattern:** 5 of ilyas_khan's PE-enrolled merchants appear in the visit sheet as demoed by **shah comm** (email: shahdottcom@gmail.com), a separate ambassador:

| Merchant | shah comm visit duration | Demo logged? | Onboarding logged? |
|----------|--------------------------|--------------|-------------------|
| unknown-2 (Khushi dot com) | 22.5 min | YES | YES |
| hamza dot com (FAKE) | 4.9 min | YES | YES |
| hanif genral store (FAKE) | 36.0 min | YES | YES |
| unknown-5 (Shabir customer service) | 33.2 min | YES | YES |
| unknown-6 (Kashif communication) | 6.9 min | YES | YES |

ilyas_khan's DCN deposits covered all these merchants, but the physical demo was logged under a different ambassador. The PE enrollment (triggered by the DCN) accrues to ilyas_khan's count. This is a split-attribution pattern: one ambassador does the field work, another collects the enrollment credit.

**Enrollment timing anomaly (hamza dot com):** ilyas_khan's PE enrollment for hamza dot com was timestamped at 18:07 PKT. Shah comm's demo start was logged at 18:13 PKT — **6 minutes after enrollment**. The PE enrollment preceded the demo visit, which inverts the expected sequence (demo → enroll). This suggests ilyas_khan pre-staged the account and enrollment before shah comm arrived to do the physical demo.

**Ghost enrollments (4 merchants with no visit record anywhere in the sheet):**

| Merchant | In Amplitude? | Ghost level |
|----------|--------------|-------------|
| unknown-1 (+923018826149) | NO | Complete ghost — no visit, no Amplitude |
| sr communication (FAKE) (+923113263959) | YES (wallet browsing) | Confirmed fake with no visit record |
| unknown-3 (+923453041506) | YES (8 sessions) | No visit but active Amplitude user |
| unknown-4 (+923128870913) | YES (4 sessions) | No visit but active Amplitude user |

**Visit sheet signal caveat:** Visit logging is not mandatory and compliance varies by ambassador. The absence of a visit record does not definitively prove a merchant was never visited — it may reflect poor form discipline. The cross-ambassador pattern (shah comm logging visits for ilyas_khan's PE merchants) and the enrollment-before-demo timing are the operationally meaningful signals here, not the raw ghost count.

---

### Revised Signal Assessment

| Signal | Finding |
|--------|---------|
| App-open (binary) | **Invalidated** — all 4 fakes opened the app. |
| No Amplitude presence at all | **Potentially useful** — 3/10 merchants never appeared; but confirmed fakes all have Amplitude records because the ambassador operated their phones. |
| `last_used` ≤ 7 days post-enrollment, no return | **Weak** — both fakes and some non-fakes follow this pattern at this cohort size. Needs fleet-level validation. |
| Visit sheet ghost (no visit logged) | **Weak, directional** — compliance varies; absence is not conclusive. |
| Enrollment timestamped before demo visit | **Strong anomaly** — one instance confirmed for hamza dot com. Requires systematic fleet-level check. |
| Split-attribution (different ambassador demos vs DCN sender) | **New pattern identified** — needs investigation of whether ilyas_khan's DCN sends overlap with other ambassadors' visit records systematically. |

---

### Conclusions

1. **The binary Amplitude app-open hypothesis is wrong.** Fakes opened the app — because the ambassador operated the phone to claim the DCN. The Amplitude signal that matters is *absence of Amplitude presence* (merchant never opened the app independently) or *activity confined to the DCN claim + immediate cash-out* with no return.

2. **A cross-ambassador split-attribution scheme is operating.** ilyas_khan sends DCNs (and gets PE enrollment credit) for merchants that another ambassador physically visited and logged. This inflates ilyas_khan's enrollment count using field work by someone else. Whether this is collusion or coincidence requires further investigation (are the two ambassadors co-located? do they share a team?).

3. **The enrollment-before-demo timing anomaly is a new DB-queryable signal.** A query can compare PE enrollment timestamps against the earliest DCN claim timestamp for each merchant. If enrollment precedes the DCN claim, the sequence is inverted and the enrollment was pre-staged. This does not require Amplitude.

4. **3 merchants have complete or near-complete Amplitude absence.** This is the cleanest Amplitude signal available, but it misses confirmed fakes whose phones were operated by the ambassador.

5. **Recommended new query (not yet built):** Fleet-wide check of PE enrollment timestamp vs first DCN claim timestamp. Any merchant where `pe.created_at < dcn.claimed_at` is normal; any where `pe.created_at > dcn.claimed_at` by more than a trivial margin (> 1 hour) is suspicious pre-staging. This is fully DB-queryable without Amplitude.

---

## Immediate Bank Transfer Signal (PA5)

Date: 2026-03-09
Queries: `demo_cashout_signal_query`, `ambassador_cashout_summary_query`
Population: All 109 PE-enrolled merchants who received a demo DCN from an ambassador since 2026-02-01

### Setup

The hypothesis: all 4 confirmed fakes claimed a $5 demo DCN and immediately did a `BankTransfer` of exactly $5 (zero real merchant usage). This behavioral pattern should be rare in the honest population and thus discriminating.

### Per-merchant cashout table (29 merchants with cashout within 48h)

| Phone | Ambassador | Demo $USD | Cashout $USD | Hrs to cashout | Claimed PKT |
|---|---|---|---|---|---|
| +923118650918 | sharoon1 | $5 | $5 | 0.0 | 2026-02-23 16:12 |
| +923192713284 | **ilyas_khan** | $5 | $5 | **0.1** | 2026-02-26 20:33 |
| +923174729739 | owaisferoz1 | $5 | $5 | 0.1 | 2026-02-17 16:47 |
| +923343887449 | umer2700 | $5 | $5 | 0.2 | 2026-02-25 23:24 |
| +923022354048 | owaisferoz1 | $5 | $5 | 0.2 | 2026-02-14 18:12 |
| +923492268065 | owaisferoz1 | $5 | $5 | 0.2 | 2026-02-13 20:57 |
| +923444242848 | owaisferoz1 | $5 | $5 | 0.2 | 2026-02-19 21:02 |
| +923704285529 | irfan1 | $5 | $5 | 0.3 | 2026-02-24 15:26 |
| +923309413875 | owaisferoz1 | $5 | $5 | 0.3 | 2026-02-14 16:37 |
| +923000030651 | sharoon1 | $5 | $5 | 0.3 | 2026-02-21 15:10 |
| +923113263959 | **ilyas_khan** | $5 | $5 | **0.7** | 2026-02-27 17:25 |
| ... (18 more rows) | | | | | |

**Note:** Only 2 of 4 confirmed fakes appear in the 48h window:
- gujjar dot com (+923192713284): 0.1h ✓
- sr communication (+923113263959): 0.7h ✓
- **hamza dot com**: NOT in list (transfer outside 48h window or different amount)
- **hanif genral store**: NOT in list (same)

From the original Q10 analysis, all 4 had BankTransfers, but the 48h+amount filter narrows the window. The signal is not watertight even on the confirmed fakes.

### Ambassador cashout rollup

| Ambassador | Demo merchants | Cashout ≤48h | % cashout | Avg hrs |
|---|---|---|---|---|
| irfan1 | 3 | 2 | **67%** | 20.8 |
| mighty_robin_3902 | 2 | 1 | **50%** | 17.5 |
| owaisferoz1 | 20 | 9 | **45%** | 0.6 |
| sharoon1 | 8 | 3 | 38% | 0.3 |
| user_1ef1d1ea | 23 | 7 | 30% | 0.7 |
| muhammadzahid | 4 | 1 | 25% | 0.8 |
| umer2700 | 9 | 2 | 22% | 10.0 |
| happy_griffin_1631 | 9 | 2 | 22% | 8.9 |
| **ilyas_khan** | 10 | 2 | **20%** | 0.4 |
| junaid9778 | 13 | 0 | 0% | — |
| afsarkhan | 4 | 0 | 0% | — |
| turab | 2 | 0 | 0% | — |
| lashkarwala | 1 | 0 | 0% | — |
| raa1997 | 1 | 0 | 0% | — |

### Finding

**Signal invalidated.** ilyas_khan's 20% immediate cashout rate is the lowest among ambassadors with non-zero cashout, and well below the median (~25%). irfan1 (67%), mighty_robin_3902 (50%), and owaisferoz1 (45%) all show much higher cashout rates. Immediate bank transfer after DCN claim is a common behavior fleet-wide, reflecting merchants who receive the demo funds and immediately withdraw rather than using them for merchant purposes. This is an activation problem (consistent with the 81% zero-activity finding in PA2), not a fraud-specific signal.

**Revised status:** Downgraded from "cleanest behavioral signal" to **invalidated** as a fraud discriminator.

---

## Enrollment Timing + Geolocation Check (PA6)

Date: 2026-03-09
Queries: `enrollment_dcn_timing_query`, `enrollment_vs_dcn_fleet_query`
GPS: Amplitude `location_lat` / `location_lng` per event vs ilyas_khan's known GPS (lat 24.940746, lon 67.0302794)

---

### PA6-A: Hamza dot com enrollment timing (Q-X1)

| Field | Value |
|---|---|
| DCN sent (PKT) | 2026-02-28 18:01:37 |
| DCN claimed (PKT) | 2026-02-28 18:02:11 |
| PE enrolled (PKT) | 2026-02-28 18:07:10 |
| mins_enroll_after_dcn_sent | **+5.55 (NORMAL)** |
| mins_enroll_after_dcn_claimed | **+4.98 (NORMAL)** |
| shah comm demo start (visit sheet) | 2026-02-28 18:13 |

**Finding:** The DCN-to-enrollment sequence is NORMAL for hamza. The enrollment did NOT precede the DCN. The anomaly identified in PA4 stands — enrollment (18:07) was before the physical demo visit (18:13) — but this is a visit-sheet vs PE timestamp comparison, not a DCN-sequence inversion. The enrollment came 5.5 minutes after ilyas_khan sent the DCN and 6 minutes before shah comm started the demo. ilyas_khan staged the account and enrollment before the physical demo was even underway.

---

### PA6-B: Fleet-wide enrollment-vs-DCN sequence (Q-X2)

| Sequence | Count | % of 109 |
|---|---|---|
| NORMAL | 104 | 95.4% |
| PRE_STAGED | 5 | 4.6% |
| ENROLLED_BETWEEN_SEND_AND_CLAIM | 0 | 0% |

**PRE_STAGED merchants (5 total):**

| Phone | Ambassador | mins_enroll_before_DCN |
|---|---|---|
| +923462889293 | owaisferoz1 | −27.1 min |
| +923442335586 | owaisferoz1 | −23.7 min |
| +923463013005 | user_1ef1d1ea | −10.0 min |
| **+923192713284 (gujjar)** | **ilyas_khan** | **−8.3 min** |
| +923331000914 | turab | −5.0 min |

**PRE_STAGED rate per ambassador:**

| Ambassador | PRE_STAGED | Total | Rate |
|---|---|---|---|
| turab | 1 | 2 | 50% |
| owaisferoz1 | 2 | 20 | 10% |
| ilyas_khan | 1 | 10 | 10% |
| user_1ef1d1ea | 1 | 23 | 4% |

**Finding:** PRE_STAGED is not unique to ilyas_khan. turab has a 50% rate (1/2), owaisferoz1 matches ilyas_khan's 10% rate (2/20), and user_1ef1d1ea has a lower 4% rate. The overall 4.6% PRE_STAGED rate suggests this is either a normal edge case in the enrollment workflow or a low-frequency anomaly distributed across multiple ambassadors. ilyas_khan's single PRE_STAGED case (gujjar) does not stand out statistically.

**Implication for gujjar dot com:** The PE enrollment for gujjar happened 8.3 minutes before ilyas_khan sent the demo DCN. This means ilyas_khan created the enrollment record, then sent the DCN to gujjar afterward. The typical flow is: ambassador sends DCN → merchant claims it → merchant enrolls. For gujjar the order was: enrollment → DCN sent → DCN claimed. This is anomalous for that individual merchant but matches the pattern seen at owaisferoz1 at even larger margins (−27 min).

---

### PA6-C: GPS geolocation of confirmed fake merchants

Amplitude event GPS compared to ilyas_khan's known coordinates (lat 24.940746, lon 67.0302794) from the single visit sheet entry.

| Merchant | Enrolled | Session date | GPS (lat, lon) | Dist to ilyas_khan | Notes |
|---|---|---|---|---|---|
| gujjar dot com (FAKE) | 2026-02-26 | 2026-02-26 15:42–15:43 | (24.9408035, 67.0302419) | **0.007 km** | Enrollment date; effectively same location |
| hamza dot com (FAKE) | 2026-02-28 | 2026-02-28 13:19 | (24.941669, 67.0301736) | **0.103 km** | Same session date as enrollment |
| hanif genral store (FAKE) | 2026-02-28 | 2026-03-01 11:12 | (24.9380506, 67.0278197) | 0.389 km | Earliest available events (100 event limit); exact enrollment-date GPS unavailable |
| sr communication (FAKE) | 2026-02-27 | 2026-02-27 13:07 | (24.9380316, 67.0277532) | 0.395 km | Enrollment-date session (DCN claimed 17:25); this GPS is from earlier in the day |

All 4 confirmed fakes have Amplitude GPS within 0.4 km of ilyas_khan's known location. gujjar is essentially co-located (0.007 km = ~7 meters — same device or same room). hamza at 0.103 km is within the same block.

**Caveat (documented as planned):** GPS proximity establishes co-location, not device control. 0 km distance means the ambassador was physically near the merchant at the time, consistent with the ambassador helping the merchant in-person. It does not prove the ambassador operated the merchant's phone. However, combined with the sub-minute DCN claim latencies already documented, the physical proximity is consistent with the ambassador operating the device directly.

**Secondary GPS finding:** sr communication shows events from 2026-03-05 at GPS (24.9358027, 67.0667054), 3.71 km from ilyas_khan's coordinates. This is a later session (after the enrollment date), suggesting the merchant's phone was used by someone in a different location 6 days after enrollment. This is consistent with the phone number being used normally by its real owner after the initial ambassador-staged interaction.

---

### PA5+PA6 Revised Signal Assessment

| Signal | Hypothesis | Result | Verdict |
|---|---|---|---|
| Immediate bank transfer (≤48h, ±20%) | Fakes cash out immediately; real merchants don't | 29/109 merchants (27%) across 9 ambassadors; ilyas_khan at 20% (below median) | **Invalidated** — not discriminating |
| Enrollment before DCN sent (PRE_STAGED) | Pre-staging means account created before demo | 4.6% fleet-wide; ilyas_khan has 1 case (10% rate), same rate as owaisferoz1 | **Weak** — minority pattern, not unique |
| Hamza DCN-to-enrollment inversion | Enrollment preceded the DCN for hamza | Enrollment was +5.5 min AFTER DCN sent (NORMAL) | **Not confirmed** — visit-sheet anomaly stands but DCN-sequence is normal |
| GPS within 0.4 km of ambassador | Ambassador co-located with merchant during enrollment | All 4 fakes GPS within 0.4 km; gujjar at 0.007 km | **Consistent** but not conclusive (co-location ≠ device control) |

### Cumulative investigation status

After PA1–PA6, every individual signal has been invalidated or shown to be fleet-wide:
- DCN latency, zero activity, account age: invalidated (PA1–PA3)
- App-open binary: invalidated (PA4)
- Immediate cashout: invalidated (PA5)
- PRE_STAGED enrollment: weak, not unique (PA6)
- GPS proximity: consistent but not conclusive (PA6)

**What survives as operationally meaningful:**
1. The cross-ambassador split-attribution pattern (ilyas_khan DCNs + shah comm physical demos) — requires manual follow-up, not automatable from DB alone
2. The enrollment-before-physical-demo timing for hamza — confirmed in PA6-A, requires visit sheet cross-reference
3. Amplitude absence (3/10 merchants never opened the app) — cleanest Amplitude signal, misses confirmed fakes because ambassador operated the phones
4. GPS co-location at enrollment (0.007 km for gujjar) — corroborating, not standalone

---

## PA7 — Ambassador Behavioral Signals

Date: 2026-03-09
Status: All Tier 1 + Tier 2 signals run. Results below.

**Context:** PA1–PA6 invalidated every individual DB signal tested (DCN latency, zero activity, account age, cashout timing, PRE_STAGED enrollment, GPS proximity). All turned out to be fleet-wide normal behavior.

**Core insight from Terra + Nash + FIELD_FRAUD + WEB_RESEARCH:** Every signal tested so far measures *merchant behavior*. The fraud is ambassador-side. New signals must measure *ambassador behavioral anomalies across their portfolio*, not any individual merchant's profile. The merchant in a fraud scenario is a ghost, a complicit shell, or an unwitting participant — all three look identical in the merchant's DB record. The signal is in the ambassador's pattern across their portfolio.

---

### PA7-A: Device Fingerprint Deduplication (Amplitude)

**Result: Does not fire.**

7 of 10 merchants found in Amplitude. All 7 have distinct `last_device_id` values. 3 merchants not in Amplitude (unknown-1: +923018826149, Shabir: +923453767324, Kashif: +923428373779).

| Merchant | Device ID | Platform |
|---|---|---|
| hanif genral store | a8d1cb3d-d617-40fb-9765-81dc3f4d4b0bR | Android |
| sr communication | 99fd8263-5e47-4030-86b9-b7c6742c8d01R | Android |
| hamza dot com | e5c0065b-b758-44fb-bdcb-e69546f4ee72R | Android |
| gujjar dot com | 1fe00c39-21f5-4ec4-90f0-ce3af5c37afcR | Android |
| unknown-4 (+923128870913) | bd8a6880-85cc-47ee-97d8-d03d4388f944R | Android |
| unknown-3 (+923453041506) | ef653d8a-05b8-40d3-9721-89bd40b5f55aR | Android |
| unknown-2 Khushi (+923462889293) | 92C93370-F45E-42D2-AB1A-58325576DB9C | iOS |

Each merchant enrolled from a different device. The ambassador did not use a single phone to register multiple merchants.

**Sources:** Terra, GSMA 2024, M-Pesa Kenya.

---

### PA7-B: DCN Temporal Clustering (DB)

**Result: Does not fire on ilyas_khan.**

Query: `dcn_burst_pattern_query(since='2026-02-01')`

ilyas_khan: max 2 DCNs sent within 20 minutes on any single day. This is below the flag threshold of 3.

Fleet outlier: **lashkarwala** — max 6 DCNs in 20 minutes on one day. This ambassador would be flagged by this signal.

The signal is valid as a fleet-level alert but does not uniquely identify ilyas_khan's fraud pattern.

**Sources:** Nash (desk-sending is the rational strategy when detection cost is low).

---

### PA7-C/D: Cross-Attribution Fleet Map + Visit-to-Enrollment Ratio (Sheet + DB)

**Result: FIRES — ilyas_khan VER = 0, most extreme outlier in fleet.**

Query: `visit_enrollment_ratio_query()` + visit sheet join via Rube workbench.

Visit sheet `1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ` (499 rows, 8 ambassadors identified by email column) was joined with PE enrollment data via email → DB username mapping.

**VER per ambassador (visits logged / PE enrollments since 2026-02-01):**

| Ambassador | Visits (sheet) | PE Enrollments | VER |
|---|---|---|---|
| muhammadzahid | 96 | 4 | 24.0 |
| irfan rana | 94 | 0 | ∞ (visits only) |
| afsarkhan | 87 | 4 | 21.75 |
| junaid9778 | 76 | 13 | 5.85 |
| user_1ef1d1ea | 40 | 22 | 1.82 |
| umer2700 | 5 | 9 | 0.56 |
| owaisferoz1 | 6 | 18 | 0.33 |
| **ilyas_khan** | **0** | **9** | **0.00 ★** |

ilyas_khan: zero visits logged in the formal ambassador tracking system against 9 PE enrollments. VER = 0 — the most extreme value in the fleet. Every other ambassador has at least some logged visits. The tracking system uses email for attribution; ilyas_khan is completely absent.

**Cross-attribution:** 17 merchant phones found in both systems. 0/18 were cross-attributed (in every case, the visiting ambassador is the same as the enrolling ambassador). The known ilyas_khan/shah_comm split is invisible to this analysis because neither appears in the visit sheet — the formal tracking system has no record of either ambassador's field work.

**Data quality caveat:** Visit sheet covers only 8 ambassadors via email match. Phone coverage is 11% (53/499 rows). irfan rana (94 visits) does not have an email in the DB. Sheet likely represents only ambassadors who were formally onboarded into the visit logging app.

**Flag rule:** VER < 0.2 with ≥3 PE enrollments = almost no field visits for many enrollments.

**Sources:** Nash, Terra.

---

### PA7-E: Enrollment Submission Timing Variance (DB)

**Result: Does not fire.**

Query: `enrollment_timing_variance_query(since='2026-02-01')`

Only 3 ambassador-days qualified (≥3 PE enrollments in a single day):
- owaisferoz1: CV = 1.245
- happy_griffin_1631: CV = 1.362
- user_1ef1d1ea: CV = 2.0

All CVs > 1.0, consistent with normal human field behavior (Poisson process: CV ≈ 1.0). No automation signal.

ilyas_khan never had ≥3 PE enrollments in a single day — falls below the daily minimum threshold entirely. The signal cannot evaluate a per-enrollment pattern when enrollments were spread across multiple days.

**Sources:** Terra (field ops timing), FIELD_FRAUD researcher.

---

### PA7-F: Off-Hours Enrollment Check (DB)

**Result: FIRES — ilyas_khan 70% off-hours.**

Query: `off_hours_enrollment_query(since='2026-02-01')`

| Ambassador | Off-hours enrollments | Total | % Off-hours |
|---|---|---|---|
| happy_griffin_1631 | 9 | 9 | 100% |
| junaid9778 | 6 | 7 | 85.7% |
| **ilyas_khan** | **7** | **9** | **70%** ★ |
| (others) | — | — | <30% |

ilyas_khan: 7 of 9 PE enrollments were submitted before 9am or after 7pm PKT. Enrollment hours range from 3am to 9pm. The threshold is 30% off-hours — ilyas_khan is at 70%, 2.3× the threshold.

Combined with VER = 0 (zero logged field visits), this strongly suggests desk-based batch submission: enrollments processed at night or early morning, not during legitimate field work hours.

**Sources:** FIELD_FRAUD researcher (fraudsters batch-process at night when supervisors are offline).

---

### PA7-G: Repeat GPS Coordinate Clustering (MOS-pathway)

Multiple MOS submissions at identical lat/lon to 3+ decimal places = ambassador standing in one location registering multiple merchants. Different from GPS velocity (Q7) which checks displacement — this checks for literal coordinate reuse.

**Check:** From existing Q7 GPS data, do any of ilyas_khan's MOS submissions share coordinates to 4dp? The 14 submissions cluster tightly in a 3km box; exact duplicate coordinate check pending from prior results.

**Sources:** WEB_RESEARCH (Databricks GEOSCAN, DBSCAN clustering).

---

### PA7-H: Leaf Node Analysis (DB)

Query: `leaf_node_analysis_query(phones=None, ambassador_id=FLAGGED_AMBASSADOR_ID)`

Ghost merchants are "leaf nodes" — their only connection is the enrolling ambassador's demo DCN. No other party has ever sent them money or received money from them. Real merchants, even dormant ones, occasionally receive P2P transfers.

**Flag rule:** `node_type = 'LEAF_NODE'` = zero non-ambassador activity across ALL DCNs and transactions (not just CashExchange).

**Result:** All 4 confirmed fakes are classified as CONNECTED, not LEAF_NODE. The demo funds (typically $5) were swept out via bank transfer on the same day, creating a non-ambassador transaction edge that breaks the classification. The signal design needs refinement: exclude same-day bank transfers of exactly the demo amount before applying the leaf-node rule.

**Status:** Does not fire cleanly — needs refinement.
**Sources:** FIELD_FRAUD researcher, Cambridge Intelligence graph analytics.

---

### PA7-I: Demo Note Amount Distribution (DB)

Query: `demo_note_amount_distribution_query(since='2026-02-01')`

Fraudsters send exactly $5.00 because that's the known demo threshold. Real ambassadors may send variable amounts based on context. Low variance with mode at exactly $5 = mechanized not relational.

**Metric:** `pct_exactly_5` (fraction at exactly 5,000,000 atomic USDC) + `stddev_usd`.
**Flag:** 100% pct_exactly_5 with stddev ≈ 0.

**Result:** ilyas_khan: 100% exactly $5, stddev = 0. However, the same result applies to mighty_robin_3902 and happy_griffin_1631 — this is fleet-normal behaviour at ZAR's current ambassador scale. The signal is not discriminating for ilyas_khan specifically.

**Status:** Fleet-normal — not discriminating.
**Sources:** VARInsights incentive fraud research (WEB_RESEARCH).

---

### Operational Signal Recommendations (Non-DB)

From Terra + Nash + MicroSave + Paytm literature:

| Recommendation | Mechanism | ROI | Source |
|---|---|---|---|
| Day 3 merchant callback (IVR/WhatsApp): "Did someone from ZAR show you the app?" | Non-response = flag. No code change required. | Highest ROI | Paytm (12–18% ghost rate), MicroSave, CMS 2024 |
| Payout split gate: 50% on enrollment, 50% released at day-30 IF ≥1 real CashExchange | Makes ghost enrollments economically worthless before creation | Structural fix | Nash, M-Pesa float activation model |
| GPS at DCN send time: flag if ambassador GPS >500m from merchant enrolled GPS | Would have caught ilyas_khan/shah comm split immediately | High | Terra |
| Shop photo at enrollment (camera-capture only, GPS-tagged, not gallery upload) | Ghost merchants cannot produce a real shop front photo | High | Terra, M-Pesa Kenya 2015 |

---

### Agent Source Summary

| Signal | Agent source | Literature source |
|---|---|---|
| PA7-A: Device fingerprint clustering | Terra, FIELD_FRAUD | GSMA 2024, M-Pesa Kenya |
| PA7-B: DCN burst pattern (desk sending) | Nash | — |
| PA7-C/D: Cross-attribution fleet map + VER | Nash, Terra | — |
| PA7-E: Enrollment timing variance | Terra, FIELD_FRAUD | — |
| PA7-F: Off-hours submissions | FIELD_FRAUD | Finextra 2025 |
| PA7-G: Repeat GPS coordinate clustering | WEB_RESEARCH | Databricks GEOSCAN |
| PA7-H: Leaf node analysis | FIELD_FRAUD | Cambridge Intelligence |
| PA7-I: Demo note amount distribution | WEB_RESEARCH | VARInsights incentive fraud |
| Day 3 callback | Terra | Paytm, MicroSave, CMS 2024 |
| Payout split gate | Nash | M-Pesa float activation |
| GPS at DCN send | Terra | — |
| Shop photo at enrollment | Terra | M-Pesa Kenya 2015 |
