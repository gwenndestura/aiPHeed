# E131 production readiness

**Decision: no E131 component replaces the served implementation.**

| Component | Validated? | Production action |
|---|---|---|
| LLM quarterly hunger forecast (4 areas) | **No.** It fails N1, N2 and N5 at Lead 2 (shared rows) and every lead overall. | None. Keep it as a prospective candidate; score the seal as SWS publishes 2026-Q4 onward. |
| LGBM-ALL (proposed) | **No.** It overfits and loses to LLM and persistence. | None |
| Provincial model-based estimates | **No.** They cannot be validated quarterly, and they depend on the deprivation measure. | None. Any display would need the "model-based" label and owner approval. |
| Price-versus-income decomposition (X3a) | Yes, as an **analysis**: it reproduces PSA within 0.25 points | Thesis evidence, not a dashboard feature |
| Release-anchored re-issue (P-REL) | It improves persistence at Lead 2 but does not pass | Owner decision. It would change the issue rule in `target.py`. |

**What would make a component adoptable:**
1. The prospective seal scores ≥ 75 % within tolerance over at least 10 unseen quarters, with N1–N7 passing.
2. The owner approves.
3. A separate integration branch, with no frontend design change.

**Nothing was changed** in the backend, frontend, FIRI v2, FIRI3, E128, E129 or E130.
