"""E66 r4 (lead-time, PROTOCOL 2.4) and r7 (target validity, 2.7).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E66_Best_Methodology_Review/runner/r4_leads_r7_target.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e66_lib as H  # noqa: E402

np, pd = H.np, H.pd


def leads():
    S = pd.read_csv(H.SEALED["E63"], dtype={"province_code": str})
    lab = pd.read_csv(H.LABELS, dtype={"province_code": str})[["province_code", "quarter", "T43", "PS"]]
    R = S.merge(lab.rename(columns={"quarter": "target"}), on=["province_code", "target"], how="left")
    R = R[R["T43"].notna()].copy()
    R["HIGH"] = R["T43"].astype(int)
    out, pair = [], []
    for lead, g in R.groupby("lead"):
        for name, col in (("E56 procedure", "E56_p"), ("E56 price part only", "E56_p_price"), ("Persistence", "PERSIST_p"),
                          ("Majority", "MAJORITY_p"), ("Climatology", "CLIM_p")):
            out.append({"lead": int(lead), "arm": name, **H.metrics(g, col)})
        for ref in ("PERSIST_p", "CLIM_p"):
            pair.append({"lead": int(lead), **H.paired(g, ref, "E56_p")})
    # common targets across leads 1-3
    common = set.intersection(*[set(g["target"]) for _, g in R.groupby("lead")])
    for lead, g in R[R["target"].isin(common)].groupby("lead"):
        out.append({"lead": int(lead), "arm": "E56 procedure (common targets)", **H.metrics(g, "E56_p")})
    M, P = pd.DataFrame(out), pd.DataFrame(pair)
    H.write_csv(M, H.TABLES / "r4_lead_metrics.csv")
    H.write_csv(P, H.TABLES / "r4_lead_paired.csv")
    return M, P, sorted(common)


def target_validity():
    lab = pd.read_csv(H.LABELS, dtype={"province_code": str})
    lab = lab[lab["T43"].notna()].copy()
    lab["year"] = lab["quarter"].str[:4]
    hi = lab["H_all"] > 11.3
    by_year = lab.groupby("year").agg(rows=("T43", "size"), T43_rate=("T43", "mean"), PS_rate=("PS", "mean"),
                                      hunger_mean=("H_all", "mean"), hunger_above_line=("H_all", lambda s: (s > 11.3).mean())
                                      ).reset_index()
    # variance decomposition of T43 into between-quarter (regional) and within-quarter (provincial) parts
    q_mean = lab.groupby("quarter")["T43"].transform("mean")
    tot = float(((lab["T43"] - lab["T43"].mean()) ** 2).sum())
    between = float(((q_mean - lab["T43"].mean()) ** 2).sum())
    facts = {"rows": int(len(lab)), "T43_equals_PS_when_hunger_above_line": f"{int((lab.loc[hi, 'T43'] == lab.loc[hi, 'PS']).sum())}/{int(hi.sum())}",
             "rows_hunger_above_line": int(hi.sum()), "T43_rate": float(lab["T43"].mean()),
             "share_of_T43_variance_between_quarters": between / tot if tot else float("nan"),
             "quarters_all_same_label": int((lab.groupby("quarter")["T43"].nunique() == 1).sum()),
             "quarters": int(lab["quarter"].nunique()),
             "late_regime_HIGH": f"{int(lab.loc[lab['quarter'] >= H.LATE_FROM, 'T43'].sum())}/{int((lab['quarter'] >= H.LATE_FROM).sum())}",
             "hunger_is_regional": "one SWS Balance Luzon value per quarter for all five provinces"}
    H.write_csv(by_year, H.TABLES / "r7_target_by_year.csv")
    return by_year, facts


def main():
    H.verify_protocol()
    H.verify_sealed()
    M, P, common = leads()
    by_year, facts = target_validity()
    H.dump({"protocol_sha256": H.verify_protocol(), "lead_metrics": M.to_dict("records"), "lead_paired": P.to_dict("records"),
            "common_targets": common, "target_facts": facts, "target_by_year": by_year.to_dict("records")},
           H.OUT / "r4_r7.json")
    pd.set_option("display.width", 250)
    print(M[["lead", "arm", "n", "positives", "accuracy", "balanced_accuracy", "recall_HIGH", "brier", "auc"]].round(3).to_string(index=False))
    print(P[["lead", "reference", "mean_brier_diff", "ci95_lo", "ci95_hi", "quarter_wins", "quarter_losses", "sign_p", "better_by_rule"]].round(4).to_string(index=False))
    print(by_year.round(3).to_string(index=False))
    print(facts)


if __name__ == "__main__":
    main()
