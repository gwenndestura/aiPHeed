# E133 deviations and implementation notes

**No deviation changes the target, the tolerance, the 75 % requirement, the leads, N1–N7, the evaluation sets or the
selection rule.**

## V1 · Settings the protocol did not state (fixed before the first E133 run)

- **Optimizer.** L-BFGS-B on [log q_c, log q_d, ρ, log τ², log q_g] with bounds q ∈ [0.01, 100], τ² ∈ [0.01, 50],
  q_g ∈ [0.01, 20], ρ ∈ [0, 1]; two fixed starts; break variance b on the grid {0, 9, 25, 49} (0 before the break is
  in the data). β by L-BFGS-B in [0, 10] from 0.1.
- **Predictive SD** = state forecast variance + τ² + the area's median sampling variance (the E131 LLM convention).
- **ENS133 interval** half-width = z80 × mean of the two members' SDs.
- **Driver availability.** E119 drivers become available on the first E119 issue date that reports their quarter
  (`__period`), which is conservative; CPI drivers 10 days after the quarter's last month (E131 rule).
- **Ablation "only-V"** keeps the market driver's area interaction but no common-level driver.

## V2 · Coding fixes before the first complete run

- The theta/bounds handling in `fit_variances` was rewritten to a fixed 5-vector with pinned unused entries before
  any candidate result was produced (one smoke test on issue 2025-10-01 checked fit and timing only).
- `d3_events` was switched from `itertuples` to `iterrows` (hyphenated column names) before it produced output.

## V3 · Post-hoc exploratory variant HFM-X-PH1 (not in the protocol; never selectable)

After the first complete run, HFM-X's largest Lead-2 miss was 2026-Q1 (MAE 9.3): falling rice prices in 2025 pushed
the forecast **down** while hunger stayed high. This prompted one variant, **HFM-X-PH1**, in which every driver acts
as a shock only (max(z, 0)): deterioration raises hunger, but improvement does not lower it (savings depletion and
debt, the ratchet seen in 2025–26). It was added after seeing the results, so its development numbers are reported
as **post-hoc** and it is excluded from selection. It is sealed (§8) so that it can be tested prospectively.

## V4 · E132 references

PERSIST, CLIM, LLM, SEAS-LLM and the learned E132 baselines come from the exact reproduction of E132
(`out/e133_reproduction_check.json`). Their numbers equal E132's.
