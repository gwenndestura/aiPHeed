# E132 deviations and implementation notes

**No deviation changes any frozen rule.**

## V1 · Pre-result fixes

Before the first complete run, two coding errors were fixed. **No result was produced before these fixes.**
1. Extending E131's feature lists broke E131's own feature builder. E132 now keeps its own extended lists (`GROUPS132`, `feat_cols132`).
2. Four smaller defects: a duplicated region-matching line, a date-type mismatch, duplicate feature names in the hybrid LightGBM, and an unused rerun inside the seal.

## V2 · Settings the protocol did not state

All were fixed before running.
- **Break variance:** chosen by pooled maximum likelihood from the grid {0, 4, 9, 16, 25, 49}.
- **Quarter-of-year shrinkage:** n / (n + 2), as in the protocol.

## V3 · H1 is partly data-prompted

The 2025–26 alternation was visible in E110–E131 outputs before H1 was written. **SEAS-LLM's development gain (0.50 → 0.61 at Lead 2) is therefore not confirmatory.** Only the prospective seal can confirm it.

## V4 · E131 models with E132 features

The E131 learned models (RIDGE-ALL, LGBM-ALL, PSA-ONLY) were re-run with the new income and rice features, as the protocol states. Their numbers differ slightly from E131. PERSIST, LLM and DLLM reproduce E131 exactly.
