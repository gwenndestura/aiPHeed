# Deliverable 11. Objective achievement assessment (75 %)

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

| Target | Is 75 % accuracy achievable and meaningful? | Verdict |
|---|---|---|
| A. FNRI/ENNS direct provincial | No defensible HIGH/LOW classes: in 2015 no province differs from the region; ENNS has no SEs. Accuracy over five provinces moves in 20-point steps (4/5 = 80 % is one province) | **Unsupported** |
| B. PSA food poverty | Only 2 province-years are significantly above CALABARZON (Quezon 2018, 2021); the protocol needs ≥ 3 HIGH and ≥ 3 LOW, so no accuracy can be computed. Ranking and level metrics show no skill | **Unsupported** |
| C. SWS regional hunger | Accuracy 0.871 (naive persistence) is above 75 %, but always-LOW scores 0.823; balanced accuracy 0.743 | **Partially achieved** (by persistence, regional only) |
| D. Price pressure | FI10 accuracy 0.73–0.74 (Leads 1–2), below 75 %; and it is not food insecurity | **Not achieved; wrong construct** |

**Recommended measure instead of accuracy:** for provincial outcomes, rank agreement (Spearman with exact p) and level
error (MAE against the published CI); for regional hunger, balanced accuracy, HIGH recall and Brier score against
persistence. A high accuracy on one target is never used to claim success on another.
