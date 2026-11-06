# aiPHeed experiment registry, E151–E164 (provincial HFIAS moderate-or-severe, HIGH at 50)

Every experiment below used the same 72 Lead 1 test rows (ENNS2018 22, ENNS2019 25, ENNS2021 25), with chronological as-of validation. **No untouched holdout remains.** Seals for prospective scoring are listed in `docs/e154/SCORING_PROTOCOL.md`.

| ID | Hypothesis | Baseline → candidate (Lead 1) | Leakage / overfit / bias checks | Decision |
|---|---|---|---|---|
| E151 | Survey anchor + LightGBM on five groups + news beats persistence | PERS 62.5 % → **72.2 %**, Brier 0.137 | as-of rules; news shuffle: no gain | Kept as base |
| E152 | Regional + price inputs help | 72.2 % → 69.4 % | | Rejected |
| E154 | Frozen model; L0 nowcast | L0 68.1 % | | Recorded |
| E155 | Deeper news (GDELT, SunStar) improves | no improvement; lead-lag mixed | locked SunStar test | Paused |
| E156 | Maximum reliable lead from fixed C1–C6 | Lead 1 fails C1 and C4 → max lead 0 | leakage test passes | Criteria fixed |
| E157 | Root causes; downloaded sources ranked | only consumption +1 row | | Diagnostics |
| E158 | E151 + PSA regional consumption | 72.2 % → **73.6 %**, Brier 0.1344 (Δ −0.003, n.s.) | sealed f69e7a02 | **Thesis model** |
| E159 | E158 orders provinces within region | concordance 0.60 vs latest survey 0.70 | criteria fixed first | Ordering fails |
| E160 | Survey-anchor arms fix ordering | RP+R 0.70; OH+R 77.8 % (not adopted) | corruption leakage 0.0 | RP+R adopted, later revoked |
| E161 | Overfit and bias audit | nested 72.2 %; triggers ≤ shuffled; LOW +5 pts | | 77.8 % = selection optimism |
| E162 | SS state space as priority method | SS 0.70, fails swap-shuffle test | bias by group | Order not validated |
| E163 | RSS / ridge / LGBM on RSS | C1 calibration pass, bias +7.2; C2 Brier 0.127 n.s. | own-evidence control; group shuffles | None passes S1–S7; sealed 343d1f06 |
| E164 | Nested automatic selection (procedure scored) | E158 73.6 % → **AUTO 79.2 %**, Brier 0.1223 (Δ −0.012 [−0.042, +0.020]) | triggers beat shuffled −0.038 [−0.063, −0.012]; news no value; leakage 0.0; C4 fails | Release candidate, **withdrawn in E165** (used test-selected consumption inputs); seal cbfb61dc kept as a record |
| E165 | Final: AUTO-FINAL without test-selected features, calibration in inner selection | E158 73.6 % → AUTO-FINAL **73.6 %**, Brier 0.1213 (Δ −0.013 [−0.036, +0.008]); McNemar 5/5 p = 1.0 | leakage 0.0; shuffle −0.006 n.s.; calibration slope 1.73; 2021 −8 pts | **Not accepted. E158 final**; no lead reliable |
| E166 | E164 + source choice nested in training-only selection | E158 73.6 % → **E166 76.4 %** (L2 79.2 %), Brier 0.1247 (Δ −0.010 n.s.); consumption chosen in 2/3 rounds | leakage 0.0; beats shuffled −0.035 [−0.063, −0.009]; C4 fails | Not accepted (F5 +3.25, F7 2021 −8 pts, F10); strongest legitimate candidate; live consumption data missing |
| E167 | E166 + round-held-out inner folds + calibration in selection | 66.7 % (L1), Brier 0.156, bias +6.3 | real inputs worse than shuffled; consumption worse than shuffled | **Not accepted; E158 final. No further experiments** |
| FINAL AUDIT | Reproduce all results; resolve the C4 definition; seal ENNS 2022 | All metrics reproduce (12 tests pass); C4 = logit-level slope (authoritative) vs probability slope (supplementary); ENNS 2022 sealed 49e514d2, no public outcomes | no model fitted | **RETAIN E158**; docs/final/ |
| E168 | LightGBM-only nested (baseline + LightGBM change + calibration layer) | L1 75.0 % (54/72), Brier 0.123; L2 77.8 % | leakage 0.0; shuffle −0.0003 n.s.; market ablation −0.0073 [−0.0154, −0.0001]; C4 0.76 | **IMPROVED BUT NOT ACCEPTED**; E158 stays; max lead 0 |
| E169 | Why C1/C4 fail; new-signal routes; FIES→HFIAS bridge | error = round/region level drift (2015 anchor); oracle level → 80.6 %; SWS/FIES wrong or absent; provincial prices already in; bridge 2019 fit, 2021 test MAE 3.0 pts | diagnostics only | Bridge feasible for regional level (±3 pts drift); docs/final/E169_* |
| E170 | Two-part LightGBM: bridged regional level + LightGBM provincial deviation | protocol locked (a886f20d); L1 **65.3 %** (47/72), Brier 0.178; bias +9.2/+6.3/+6.9 (held level misses drift); C4 passes | leakage 0.0; shuffle +0.006 [−0.0014, +0.0146] fails | **NOT ACCEPTED**; E158 stays; seals af0180af (ENNS 2022), df03d885 (2027-Q1) |
| E168-SEAL | Frozen E168 sealed for ENNS 2022 (156 rows, origin O3) before any 2022 outcome | sha256 f8228fae | procedure unchanged since b11aa542 | Sealed |
| E171 | Level-change LightGBM + E170 calibrated deviation (INFORMED design) | protocol locked (996d08ce); L1 **72.2 %** (52/72), L2 76.4 %, Brier 0.148; HIGH recall 0.92; 2021 round 84 %, bias −0.8; 2018/19 +7.3/+5.3 | leakage 0.0; shuffle +0.0118 [−0.0008, +0.0267] fails; C1, C4 fail | **NOT ACCEPTED** (retrospective not acceptance evidence); seals a929929a (ENNS 2022), 1559746c (2027-Q1) |
