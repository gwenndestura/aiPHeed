"""Five-contributor audit of the served dashboard (thesis mode): every served province-quarter's trigger bars, statuses
and hidden share, checked against the served model's own inputs. Run from backend/ with AIPHEED_LEAD2_MODEL=thesis.

    python ../aipheed-backend-aligned/experiments/LEAD2_OPTIMIZATION/runner/contrib_audit.py [tag]
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path.cwd()))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from app.ml.inference import ch1_system as CH1  # noqa: E402
from app.services import dashboard as DB  # noqa: E402
import l2_lib as X  # noqa: E402

TAG = sys.argv[1] if len(sys.argv) > 1 else "before_fix"
OUT = HERE.parent / "out"
GROUPS = {"market": ["A1_food", "A1_gap", "A_mom", "A2", "A3", "W_rice_yoy", "W_rice_mom", "W_cereal_yoy", "W_crude_yoy"],
          "climate": ["C1", "C2", "C3", "W_urea_yoy"], "fish_kill": ["C4"], "employment": ["E1"], "ofw_remittance": ["E2"]}


def main():
    X.U.setup()
    L = X.L
    S = X.U.stack(4)
    rows = []
    for (code, q), r in CH1.rows().items():
        lead = int(r["lead"])
        t = L.qi(q) - lead
        srow = S[(S.t == t) & (S.lead == lead) & (S.province_code == code)]
        e = DB.explainability(code, q)
        for tr in e["triggers"]:
            avail = None if srow.empty else bool(srow[GROUPS[tr["key"]]].notna().any(axis=1).iloc[0])
            rows.append({"province": r["province"], "quarter": q, "lead": lead, "group": tr["key"], "pct": tr["pct"],
                         "signed": tr["signedContribution"], "status": tr["status"],
                         "inputs_available_in_model": avail, "otherPct": e.get("otherPct"),
                         "evidenceNote": tr["evidenceNote"]})
    A = pd.DataFrame(rows)
    A.to_csv(OUT / f"contributor_audit_rows_{TAG}.csv", index=False, lineterminator="\n")
    lines = [f"[{TAG}] served rows: {A[['province', 'quarter']].drop_duplicates().shape[0]} | group rows: {len(A)}"]
    mis = A[(A.status == "insufficient_data") & (A.inputs_available_in_model == True)]  # noqa: E712
    lines.append(f"'insufficient_data' although the served model had a published input: {len(mis)} of "
                 f"{int((A.status == 'insufficient_data').sum())}; by group {mis.groupby('group').size().to_dict()}")
    mis2 = A[(A.status.isin(['contributes', 'no_effect'])) & (A.inputs_available_in_model == False)]  # noqa: E712
    lines.append(f"'contributes'/'no_effect' although every input was missing: {len(mis2)}")
    lines.append(f"status counts: {A.status.value_counts().to_dict()}")
    o = A.drop_duplicates(["province", "quarter"]).otherPct
    lines.append(f"otherPct (share of |SHAP| in V1, N1, H1, outside the five bars that are rescaled to 100 percent): "
                 f"mean {o.mean():.1f}, min {o.min():.1f}, max {o.max():.1f}")
    dom = A.loc[A.groupby(["province", "quarter"]).pct.idxmax()].group.value_counts()
    lines.append(f"top group per served row: {dom.to_dict()} | bars at 100 percent: {int((A.pct == 100).sum())}")
    R = pd.DataFrame(CH1.rows().values())
    lh, lp = np.log(R.pi_hunger.astype(float).clip(1e-6)), np.log(R.pi_price.astype(float).clip(1e-6))
    v = np.var(lh + lp)
    lines.append(f"variance share of log P(HIGH) over served rows: hunger term "
                 f"{(np.var(lh) + np.cov(lh, lp)[0, 1]) / v:.2f}, price term {(np.var(lp) + np.cov(lh, lp)[0, 1]) / v:.2f}")
    sh = R[[c for c in R.columns if c.startswith("shap_")]].astype(float).abs()
    lines.append(f"mean |SHAP| share by family: {(sh.mean() / sh.mean().sum()).round(3).to_dict()}")
    lines.append(f"evidence note (market, first row): {A.evidenceNote.iloc[0]}")
    (OUT / f"contributor_audit_{TAG}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
