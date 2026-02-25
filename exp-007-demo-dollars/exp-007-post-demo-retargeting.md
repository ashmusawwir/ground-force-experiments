# EXP-007: Post-Demo Retargeting

**STATUS:** ANALYZING

## Scorecard
Metrics TBD — pending first code run.

## Hypothesis
Revisiting demoed-but-not-onboarded merchants on a subsequent day converts at a higher rate than single-visit merchants.

## Success Criteria
- Retargeted conversion rate > not-retargeted conversion rate by >=10pp
- Retarget pool >= 30 merchants (sufficient N)

## The Experiment
Retrospective analysis of existing visit form data. For merchants who received a demo but didn't onboard on the first visit:
- Were they revisited on a different calendar date?
- Did revisiting improve their conversion to onboarding?

## Minimum Viable Test
Analyze all onboarding visits with phone numbers from the shared visit form (same sheet as EXP-001/002/006). Group by merchant phone, classify into retargeted vs not-retargeted, compare conversion rates.

## Results
Pending first code run.

## What Happens Next
If retargeting converts higher: build systematic retargeting protocol for ambassadors.
If no difference: focus ambassador time on new merchants instead of revisits.

## Detail
- Data source: Google Sheet `1bFf0NAQFFXIYYxMC1yJeqowRz6MwT_-xawZeg5H9wUQ`
- "Retarget pool" = demoed on first visit + NOT onboarded on first visit
- "Retargeted" = pool members visited on 2+ different calendar dates
- Conversion = ever onboarded (QR setup done on any visit)
- Phone coverage gap: rows without phone numbers excluded from analysis
