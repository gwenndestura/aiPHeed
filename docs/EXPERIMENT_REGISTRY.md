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
| E164 | Nested automatic selection (procedure scored) | E158 73.6 % → **AUTO 79.2 %**, Brier 0.1223 (Δ −0.012 [−0.042, +0.020]) | triggers beat shuffled −0.038 [−0.063, −0.012]; news no value; leakage 0.0; C4 fails | **Release candidate**, sealed cbfb61dc, not deployed |
