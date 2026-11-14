# E192: trajectory-consistent, correlation-preserving synthetic rows ("trajcorr"). Fixed before results. Local only.

Written 2026-11-10 at the owner's request ("fix it"), after E191.

## Weaknesses in E191 being fixed
- **Its probabilities were worse:** the nested `traj` arm's Brier was worse than E184's at Leads 1–3.
- **No gain at Lead 1.**
- **It fell below 75 % at Leads 5–6.**

## Diagnosis and fix
1. **Uncorrelated noise.** `traj` adds independent noise to each input. That breaks the real joint movement of prices,
   climate, jobs and the other inputs. The two generators E191 ranked best on separate evidence were:
   - `traj`, best on the training side at all three origins;
   - `corrnoise`, best outer Brier.
   **Fix:** combine them. Each synthetic province-round trajectory gets one shared noise vector drawn from
   N(0, 0.25 Σ_class), where Σ_class is the class's Ledoit-Wolf covariance of the standardized continuous inputs (training
   rows only). The outcome is redrawn once per trajectory: y + N(0, se). Parents are chosen by the `traj` rules:
   boundary focus and E184's class allocation.
2. **Draw noise.** One E184 draw moves accuracy by 3–6 points. **Fix:** an arm with 20 draws (17901–17920).
3. **Stream artefact.** In E191, leads that shared a training frame shared one random stream. **Fix:** every (survey,
   lead) is its own job with its own stream, so E184 reproduces exactly.

## Arms
- Everything else is E184: 50/50, weight 1.0, E168 selection, calibration and frames (from E191).
- **Arms:**
  - **E184** (re-run, which must equal the stored rows);
  - **traj** (E191's generator, the "before" arm);
  - **E192 = trajcorr, 5 draws** (primary);
  - **E192_20 = trajcorr, 20 draws.**

## Test
- **Rows and metrics.** Leads 1–6, 72 real rows per lead. Accuracy, false alarms, misses, balanced accuracy and Brier.
- **Paired comparisons with E184.** Brier CI (region-cluster bootstrap, 2,000 draws) and exact McNemar.
- **Owner rule.** Reported per lead.

## Decision (E188's rule)
- **An arm is preferred to E184 only if all three hold:**
  - accuracy ≥ E184's at all six leads;
  - Brier ≤ E184's at all six leads;
  - accuracy higher at at least one lead.
- **If both arms qualify,** the lower mean Brier wins. Otherwise E184 stays.
- **80 % target.** Reported separately.
- **Scope.** Nothing is staged, committed or pushed.
