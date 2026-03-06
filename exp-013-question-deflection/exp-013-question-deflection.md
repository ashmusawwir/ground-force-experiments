# EXP-013: Question Deflection Tool

**STATUS: DESIGN** — Building a physical deflection guide (mobile HTML) with scripted redirect phrases for the 8 most common merchant question/objection types. Parent: EXP-006.

---

## Scorecard

| Metric | Baseline | Current | Target |
|--------|----------|---------|--------|
| Q→Demo rate | 25% (EXP-006 pre-training, 43/172) | — | 60% (SHIP) |
| Deflection coverage | 5 categories (training only) | — | 8 categories (scripted tool) |
| Sample | — | — | ≥100 question-askers post-deployment |

## Hypothesis

IF ambassadors are equipped with a scripted deflection tool (mobile HTML with redirect phrases for 8 question types) THEN Q→Demo rate reaches ≥60%, vs 25% baseline BECAUSE the tool eliminates hesitation about *what to say* under pressure — the remaining gap after redirect training alone.

## Success Criteria

- **SHIP if:** Pooled Q→Demo ≥60% AND ≥3/5 ambassadors individually above 50% → Roll out tool to all ambassadors, embed in onboarding training
- **ITERATE if:** Pooled Q→Demo 45–59% OR improvement driven by ≤2 ambassadors → Refine scripts based on which categories still drop off, run another cycle
- **SHELVE if:** Pooled Q→Demo <45% → Tool doesn't add enough over training alone; investigate whether bottleneck is demo skill, not redirect timing

**Confirmation metric:** E2E onboarding rate must not decline. A faster path to demo is worthless if demos don't convert.

## The Experiment

EXP-006 found that 75% of question-asking merchants never see a demo — ambassadors get stuck in verbal Q&A. Training on a redirect phrase moved behavior directionally, but relied entirely on memory under pressure. This experiment gives ambassadors a physical tool: a mobile-friendly HTML page with scripted redirects for each question type, so the right words are always at hand.

**Notes mining (1,481 field notes, Roman Urdu)** revealed 3 objection categories the original 5 miss:

| New Category | Evidence | Example verbatim |
|-------------|----------|------------------|
| Fees & Commission | 124 form entries | "Kya commission hai?" |
| No Demand Here | ~80+ notes | "Yaha dollar ka customer nahi hai" / "Kon kharide ga dollar" |
| Already Have a Solution | ~30+ notes | "Easypaisa jazzcash or easy load m bohat masroof hun" |

Other common note themes (owner absent, CNIC issues) are operational blockers, not question-deflection targets.

## Minimum Viable Test

- **Intervention:** Mobile HTML deflection guide shared via WhatsApp — ambassadors save to phone / home screen
- **Who:** All active ambassadors (same roster as EXP-006)
- **How:** Before/after deployment. No true control group (same limitation as EXP-006).
- **Duration:** 7 days post-deployment (one full work week)
- **Measurement:** Same visit form — `wantsDemoAfterQuestions` already captures redirect outcome. No new self-report fields needed (Nash-approved). Auto-captured `questions_end_time` timestamp measures redirect speed.
- **Controls:** Same form, same visit areas, same ambassador roster. Only change: deflection tool in hand.

## Results

### What happened

*Pending deployment.*

### What we learned

*Pending.*

### What we'd do differently

*Pending.*

**Decision:** —
**Decision notes:** —

## What Happens Next

- **If SHIP:** Distribute deflection guide as standard ambassador equipment. Embed in onboarding training for new hires.
- **If ITERATE:** Analyze per-category dropoff to identify which scripts need rewriting. Terra re-tests against personas.
- **If SHELVE:** Bottleneck is likely demo execution quality, not redirect timing. Pivot to EXP-009 (Demo Shadow) findings.

## Detail

### Deflection Guide Categories

| # | Category | Redirect Phrase (EN) | Redirect Phrase (UR) |
|---|----------|---------------------|---------------------|
| 1 | Company Info | "Let me show you on the app — 30 seconds." | "App pe dikha deta hoon — 30 second lagenge." |
| 2 | How It Works | "Easier to show than explain — watch this." | "Batane se zyada dekhna asaan hai — ye dekhein." |
| 3 | Trust & Safety | "Fair question. Look — your money, your control." | "Bilkul sahi sawaal. Dekhein — aapka paisa, aapka control." |
| 4 | Legal & FIA | "Fully registered. Let me show you the proof." | "Puri tarah registered hai. Proof dikha deta hoon." |
| 5 | Withdrawals | "Cash out anytime. Let me show the process." | "Kisi bhi waqt paisa nikal sakte hain. Process dikha deta hoon." |
| 6 | Fees & Commission | "Zero hidden fees. Let me show you a live transaction." | "Koi chhupi fee nahi. Ek live transaction dikha deta hoon." |
| 7 | No Demand Here | "Your neighbors are already earning. Let me show you." | "Aapke aas-paas ke log kama rahe hain. Dikha deta hoon." |
| 8 | Already Have a Solution | "This works alongside JazzCash — extra income, no conflict." | "Ye JazzCash ke saath chalta hai — extra kamai, koi masla nahi." |

### Notes Mining Summary

Source: EXP-006 Google Sheet (`1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ`), Notes column, 1,481 non-empty entries in Roman Urdu.

**Top objection clusters (translated):**
1. "Don't trust online apps / past fraud" — ~200+ entries
2. "Owner/brother not present" — ~150+ (operational, not deflectable)
3. "Not interested in dollars / no relevance" — ~100+
4. "No dollar customers in this area" — ~80+
5. "Already using EasyPaisa/JazzCash" — ~30+
6. "Cash-only business" — ~25+
7. "Don't understand dollar trading" — ~30+
8. "Need to verify/research first" — ~30+

### Methodology

Same clustering limitation as EXP-006: 5 ambassadors = 5 clusters. All claims directional. Ambassador-stratified analysis required.

### Prior Experiments

| EXP | Finding | Implication |
|-----|---------|-------------|
| EXP-001 | Demo-first opener: 61% pass-through, but Q→Demo only 25% | Identified the Q&A bottleneck |
| EXP-006 | 75% of question-askers never see a demo; training improved behavior directionally | Training alone insufficient — need a physical tool |

### Gate Log

| Date | From | To | Rationale | By |
|------|------|-----|-----------|-----|
| | | | | |

**Kill criteria:**

| Check | Trigger | Authority |
|-------|---------|-----------|
| Mid-point (day 4) | Pooled Q→Demo below 40% with n≥40 | Turab can kill early |
| Confirmation metric | E2E flat after 5 days of Q→Demo improvement | Asharib flags, Turab decides |
| Tool adoption | ≥3 ambassadors not using the tool (observed) | Qasim escalates |
