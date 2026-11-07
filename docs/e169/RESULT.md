# E169 result (locked run, 2026-11-06)
- Valid run (leakage control). Lead 1: 56/72, C1-C6 all pass. Lead 2: 55/72, fails C1 only. Lead 3: 54/72. Max reliable lead 1.
- Identical HIGH/LOW classes to E168 at Leads 1-3; Lead-1 Brier 0.1399 vs E168 0.1394 (difference +0.0005 [0.0001, 0.0010]).
- **Decision under the pass rule: E169 does not replace E168. E168 stays the thesis model.** No further attempts on these 72 rows.

## Correction (2026-11-07)
E169's seed bagging was **never applied**: `U.LEARNERS["LGBM"] = Bag` ran only in the main process; the joblib worker processes that
made every forecast used the unbagged `Res2` (verified with a probe; see docs/e171/PROTOCOL.md §7). E169 is therefore not a test of seed
bagging. Seed bagging was applied correctly in E172 (subset BAG: Lead 2 54/72, no class improvement over E168).
