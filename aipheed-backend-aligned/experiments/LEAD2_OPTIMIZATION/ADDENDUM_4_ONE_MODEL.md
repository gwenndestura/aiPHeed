# LEAD2_OPTIMIZATION Addendum 4: ONE unified LightGBM on the combined target (hashed before any Addendum-2/3 score existed)

**When.** 2026-10-27, after your correction: one unified LightGBM for every lead, all 12 families, lead as a feature, one target, one pipeline, one horizon rule. No per-lead final models and no ensembles of separately trained models.

**Status at freezing:**
- Addendum-2 leakage audit: 5 of 6 origins done.
- Addendum-3 hunger audit: passed.
- No Addendum-2 or Addendum-3 metric existed.
- Everything is development evidence.

## 1. Architecture (the only final candidate form from now on)

**U-ONE.** One LightGBM classifier, refitted at each issue date on the stacked rows of **every lead** (1–15).

| Element | Definition |
|---|---|
| Training label | The **combined target T43c itself**, known before O(t) (`ch1_lib.known_t43c`) |
| Features | All 12 FIRI v2 families (the 16 U2 columns, including H1 = π_H); `lead`; the 5 Pink Sheet columns; and **hunger-onset inputs**: h_last (newest BL reading published before O(t)), true_horizon (target quarter minus that reading's quarter), Region IV-A rice CPI YoY and food CPI YoY at m0 |
| Monotone +1 | A1_food, A1_gap, A_mom, H1, h_last |
| Structural starting point (variant U-ONE-P only) | init_score = logit(clip(π_H × STRUCT_k, 0.01, 0.99)). STRUCT_k is the Addendum-1 structural price probability, with σ per lead from that origin's price-label rows. This is one deterministic offset inside the single model, not a second model. |
| Grid | UNI grid (8) + regularised grid (4), chosen by inner chronological validation (last 4 training origins, log-loss on T43c) |
| Eligibility | ≥ 6 target quarters, ≥ 5 HIGH, ≥ 5 LOW. Not eligible → the forecast is the structural offset itself, so every evaluation row is still scored. |
| Decision | HIGH at 0.50 |

**Hunger input (conditional rule fixed now).** If Addendum 3 adopts a sample-a hunger term other than H0 (H4 or H3a), that term replaces π_H in H1 and in the offset. Sample-b terms are never used.

**Variants:**
- **U-ONE-P:** with the structural offset;
- **U-ONE-0:** without it, same features.

## 2. Selection and verdicts

**Choosing the variant.** The final single-model variant has the lower **mean development Brier over Leads 1–4** (targets ≤ 2024-Q4). One model must serve every lead, so selection is not by Lead 2 alone. Ties within 0.0005 go to U-ONE-0 (simpler).

**Reliability per lead.**
- **Applied to:** the chosen variant at every lead 1–15, on the identical UNI-FINAL evaluation rows.
- **Rules:** R1–R7 + the Addendum-2 later-block check, as in Addendum 3 §4.
- **Maximum reliable lead:** the consecutive passing leads from Lead 1, determined from the results and never set in advance.
- **Verdicts:** Addendum 2 §3 categories. No "Reliable" verdict before untouched SWS 2026-Q4+ outcomes.

**Comparison with UNI-FINAL** (incumbent; one LightGBM with π_H as a multiplicative term), on identical rows at every lead: Brier one-sided cluster bootstrap, accuracy, recall.

**Serving** (PROTOCOL_LEAD2 §4 rule). U-ONE replaces UNI-FINAL on the dashboard only if all hold:
- reliable at Lead 1;
- maximum reliable lead ≥ 1;
- Lead-1 Brier not worse than UNI-FINAL at one-sided p < .10.

Otherwise UNI-FINAL stays served. Whether its multiplicative hunger term is acceptable under the one-model requirement goes to you as a decision.

**Before serving.** Any served U-ONE gets a new seal (issue 2026-10-01, Leads 1–15) before its first unseen outcome. Its export must reproduce the evaluated probabilities exactly.

## 3. Audits

Before scoring, the same 6-origin future-perturbation audit runs, covering:
- SWS rounds, CPI, regional CPI, Pink Sheet, news;
- T43c labels: target quarters at or after O(t) cannot be in training.

Historical replay at 3 origins follows. Post-hoc analyses:
- news ablation and 20-shuffle placebo;
- family ablation;
- onset detection (LOW → HIGH transitions) at each lead;
- calendar-time check of SHAP shares.
