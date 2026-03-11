# Angry Anecdote — Field Complaint Analysis
**Date captured:** 2026-03-09
**Merchant:** Malik Wajid Mobile, Lahore (+92 348 4852785)
**Contractor:** Irfan

---

## Transcripts

### Irfan (Contractor) — ~43s voice note

**Roman Urdu:**
> Bas yeh aap ko pata hai ke us ke customer ache lag gaye hain, ek do customer aur bhi us ke lag gaye hain. Theek hai, resend bhi us ke paanch sau dollar ka tha lena tha. To us mein us ne pehle hazaar liya tha, mere ghar se paanch sau liya tha, mujhe yaad nahin. To paanch sau lena tha. Us ke liye bhi kaafi delay ho gaya tha. Issues aa rehte the, to woh yahi lagta tha kehte ke customer aana shuru ho raha hai. To is tarah customer fareb hote hain, to issues aa rahe hain kyunke khareedari mein masla banta hai. To is tarah hona chahiye. To us ke wale se thora sa dekhenge, kyunke jab issue lagana hota to koi na koi issue aa jata hai.

**English:**
> So you know that he's gotten some good customers — one or two more have joined him too. Regarding the resend, he had $500 to receive. He first took a thousand [units] and took 500 from mine — I don't remember exactly. So he still had 500 to receive, and there's been quite a delay. Errors kept coming. It seemed like customers were starting to come, so customers get frustrated when issues come because there's a problem in the transaction. That's how it should be handled. We'll look at it from his side because whenever something needs to be set up, some error comes up.

*Context: Irfan is briefing a supervisor/manager — NOT responding directly to the merchant.*

---

### Merchant — ~52s voice note

**Roman Urdu:**
> Assalam Alaikum, Irfan bhai ki haal hai? Irfan bhai, bahut baar maine aap ko kaha hai ke aap ko masla aa raha hai — is masle ko durust karwain. Hum jab kaam kar rahe hain to aap hamare saath chalein — yeh zyada hai. Aap hamare liye kuch karte nahin hain. Hum bana bana ke tarle kar rahe hain bhai. Hum logon ko daleel de rahe hain, unko mutmain kar rahe hain, log customer bana rahe hain. To phir bhi woh nahin hal — hall karwain. Maine pehle bhi keh chuka ke meri app durust karwain. Baki koi nahin hai, nahin hai. To bhai hatam karwain meri app ka masla. Masla nahin hai Alhamdulillah — yeh meri app wazeh nahin hai. Bhai, shukar Allah bhai. Mujhe bahut sochna parta hai. Agar aap ne mujhe aise daleel dena chahte hain to meri app bhai karwain.

**English:**
> Assalam Alaikum — how are you, Irfan bhai? Irfan bhai, I've told you many times that this problem is happening — get it fixed. When we ARE working, you should stand by us — this is too much. You don't do anything for us. We keep putting in effort after effort, bhai. We convince people, make them satisfied, convert them into customers. But still the issue isn't resolved — get it resolved. I've already told you before: fix my app. There's nothing else. Just fix my app, bhai. The business is fine, Alhamdulillah — but my app is not working properly. Thank God [my business runs], bhai. I think about this a lot. If you want to keep making excuses to me, then just fix my app, bhai.

---

## Emotion Analysis

### Merchant
| Dimension | Assessment |
|-----------|-----------|
| Primary emotion | Frustration + Betrayal |
| Intensity | 4/5 |
| Tone | Assertive, escalating, repetitive (classic ignored-escalation pattern) |
| Key markers | Repeated "bahut baar kaha" (told you many times), "aap hamare liye kuch karte nahin" (you do nothing for us), "aise daleel" (making excuses) |
| Underlying state | Committed and invested — still working, still bringing customers — but feels abandoned by the support structure |
| NOT | Churned or threatening to quit — the Alhamdulillah framing signals he wants to stay |

**Core complaint:** App is broken ("app wazeh nahin" = app not displaying/working) and Irfan has not fixed it despite repeated requests. The merchant has been doing his job (convincing customers, generating business) but is blocked by an unresolved technical issue on ZAR's side.

### Irfan (Contractor)
| Dimension | Assessment |
|-----------|-----------|
| Primary emotion | Defensive, slightly deflective |
| Intensity | 2/5 |
| Tone | Explanatory, briefing upward — minimising the urgency |
| Key markers | "mujhe yaad nahin" (I don't remember), "thora sa dekhenge" (we'll look at it a bit), vague causal framing |
| Problem | Irfan is narrating the situation rather than owning it — no accountability language, no resolution committed |

---

## Merchant DB Snapshot

| Field | Value |
|-------|-------|
| Business name | Malik Wajid Mobile |
| User | Malik Kamran (`user_61163c1c`) |
| Phone | +92 348 4852785 |
| City | Lahore |
| Source | MOS (merchant_onboarding_submissions) |
| Status | **active** |
| Onboarded | 2025-09-24 |
| Onboarder | `aa46304d-8e5c-4e97-8ff0-c0906813ecf4` |
| ZCE orders (completed) | 2 (Sep–Oct 2025, pre-migration era) |
| CashNote transactions | **59** (Dec 2025 – Mar 8, 2026) |
| Total transactions | **61** |
| Last active | **2026-03-08** (yesterday) |

**Key insight:** This merchant is NOT dormant — 59 CashNote sales over ~3 months, last transaction yesterday. He's actively running ZAR, bringing customers, and his business is working. The complaint is about a UI/technical bug in the app, not about disengagement.

---

## Terra Analysis — Field Coaching Perspective

### What the complaint reveals about this merchant persona

This is a **Committed Active** persona — already converted, not at churn risk, but at support-failure risk. The danger isn't that he'll stop using ZAR; it's that he'll stop trusting the support system, which erodes his willingness to onboard future customers and refer other merchants.

His complaint pattern is textbook "repeated escalation with no response":
1. Problem reported → ignored → problem reported again → ignored → voice note escalation
2. He explicitly says "bahut baar kaha" (told you many times) — this is at least the 3rd+ escalation point
3. He's still framing it with Alhamdulillah and gratitude — he's not hostile, he's hurt

The app issue ("app wazeh nahin") is likely a UI visibility bug — possibly the merchant QR/cashout interface not rendering correctly. Given 59 CashNote transactions despite the bug, he's found a workaround — but the friction is real.

### What went wrong on the field side

**Irfan's failure mode: the relay without resolution**

Irfan's voice note is a briefing to a supervisor — it's passive escalation. He's describing the situation but not owning a fix. The phrases "thora sa dekhenge" and "mujhe yaad nahin" are classic contractor disengagement signals:
- He doesn't remember the transaction details → not tracking his merchants
- "We'll look at it a bit" → no committed timeline, no action owner
- He's treating a technical bug as a field problem he can narrate away

The merchant expected Irfan to either (a) fix it directly or (b) escalate hard to someone who can. Instead, Irfan narrated it upward with low urgency and the merchant got nothing.

**The $500 resend**: There's a separate thread about a $500 pending transaction/resend that was delayed. This may be a stuck cash note or a transaction that didn't complete. If the merchant is owed $500 in pending funds, that's a real financial grievance on top of the UX bug.

### Coaching recommendations

**Immediate (Irfan):**
1. Call back within 24h with a clear resolution timeline, not a vague "we'll look"
2. Acknowledge the repeated escalations explicitly — "I know you've been waiting, that's not acceptable"
3. Get the $500 resend resolved or escalate to support with a ticket number to share with the merchant
4. Do not send another explanatory voice note — this is a phone call situation

**Systemic (ground force ops):**
1. **Technical escalation path is missing.** Ambassadors/contractors don't have a clear path for app bugs. Irfan is floating the complaint upward informally instead of filing a support ticket. Build a protocol: bug reported → contractor opens ticket → merchant gets ticket ID within 24h
2. **Merchant support SLA.** Active merchants (59 transactions) with unresolved bugs should be auto-flagged for priority support, not handled through WhatsApp voice chains
3. **Contractor accountability.** Irfan's "I don't remember" about a $500 transaction is a flag. Contractors should log every merchant issue with a date and status. This one has clearly been sitting
4. **The good news:** The merchant is engaged, loyal, and commercially productive. This is a retainable relationship — but only if the app issue is resolved within days, not weeks

---

## Summary

The merchant is a high-value active user (61 transactions, last active yesterday) lodging a legitimate, long-standing complaint about an unresolved app bug. He's done everything right — brought customers, built the habit, stayed loyal — and feels abandoned by technical support. Irfan's response has been passive relay with no ownership. The risk is not churn; it's loss of trust that makes this merchant reluctant to evangelize or expand.

**Required action:** Resolve the app issue, call back with ticket number, acknowledge the delay. Close this within 48h.
