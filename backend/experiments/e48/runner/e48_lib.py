"""E48: align the model with THESIS_2_14 Chapter 3 (lead 1). Experiment only.

Paper (Chapter 3):
  Eq. 5 / Algorithm 2: five trigger proportions (market, climate, employment, ofw_remittance, fish_kill) = share of a
    province-quarter's articles triggering each category, entered as five features and used for SHAP attribution.
  Eq. 3 / Table 3.4.2.3: stress(p,t) = sws_hunger(t) + 2 x (food_cpi_yoy(p,t) - regional mean(t)); HIGH if
    stress > global median(stress) over ALL labelled province-quarters ("guarantees a 50/50 class balance").

E36's walk-forward (e36_lib.walk_forward: origins, training rows, grid G1/G4/G3/G2, seed 36, nested rule, threshold 0.5,
baselines) is reused unchanged; extra pools are added in memory. Trigger shares are e38_lib's (titles of quarter t,
the news window E36 already uses). stress = S1 (the served target uses the same formula).

Labels:
  current  tau(t) = trailing median of S1 over quarters posted before the origin (as served)
  paper    tau = median of S1 over ALL labelled province-quarters 2021-Q2..2026-Q3 (the paper's label definition; it
           uses the whole label period, i.e. outcomes after the origin -- a label-definition choice, not a feature)
"""
from __future__ import annotations

import sys
from pathlib import Path

E48 = Path(__file__).resolve().parents[1]
ROOT = E48.parents[2]
E38_RUNNER = ROOT / "aipheed-backend-aligned" / "experiments" / "E38_Lead2_Diagnosis_Tuning" / "runner"
sys.path.insert(0, str(E38_RUNNER))
import e38_lib as L8  # noqa: E402

L7, L6 = L8.L7, L8.L7.L6
L6.guard32.EXP = E48                       # writes confined to E48 (and the OS temp directory)
C, np, pd = L8.C, L8.np, L8.pd
qk, qs, PROVS = C.qk, C.qs, C.PROVS
TRIG = ["trig_market", "trig_climate", "trig_employment", "trig_ofw_remittance", "trig_fish_kill"]
GROUPS = {"market": ["D_last", "Dnow", "rice_rel", "trig_market"], "climate": ["trig_climate"],
          "fish_kill": ["trig_fish_kill"], "employment": ["trig_employment"],
          "ofw_remittance": ["trig_ofw_remittance"]}             # everything else = "other"


class Data(L8.Data):
    """E36 features + e38 trigger shares; lead 1. paper=True -> the paper's global-median label."""

    def __init__(self, paper: bool = False):
        super().__init__()
        self.paper = paper
        s = self.S1.dropna(subset=["S1"])
        self.tau_paper = float(s["S1"].median())
        self.tau_paper_n = int(len(s))
        self.tau_paper_range = (s["quarter"].min(), s["quarter"].max())

    def tau(self, t: int) -> float:
        return self.tau_paper if self.paper else super().tau(t)

    def train(self, t, k=1):
        return super().train(t, k)

    def test(self, t, k=1):
        return super().test(t, k)


def register_pools():
    L6.FEATURE_SETS["COMPACT_T5"] = L6.COMPACT + TRIG
    L6.FEATURE_SETS["COMB_T5"] = L6.COMB + TRIG
    L6.POOLS["E48-T5"] = ([("COMPACT_T5", g) for g in L6.COMPLEXITY] + [("COMB_T5", g) for g in L6.COMPLEXITY],
                          ("COMB_T5", "G1"))
