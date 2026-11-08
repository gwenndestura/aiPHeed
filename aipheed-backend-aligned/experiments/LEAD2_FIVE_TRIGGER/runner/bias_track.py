"""PROTOCOL_LEAD2_BIAS_TRACK (hash checked): one development candidate X1 = B0 + EF_recent, EG_recent (the CPI
projection's own most recent realised error), selected on development quarters only; secondary X1-VER on the
verified-timing CR stack. Nothing is adopted, served or resealed.

    python bias_track.py   # ../out/bias_track.json, ../out/bias_track_rows.csv
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import final as FN
import lt_lib as T
import asof_reeval as A
import lead2_rootcause as RCII
import root_cause as RC

F, KEY = T.F, T.KEY
NEW = ["EF_recent", "EG_recent"]


def add_recent(S: pd.DataFrame, Lb: pd.DataFrame) -> pd.DataFrame:
    """EF/EG_recent of row (t, k, p): realised margin of t-1 minus the lead-k projection made for t-1 at t-1-k."""
    proj = {(int(t), int(k), p): (a, b) for t, k, p, a, b in zip(S["t"], S["lead"], S["province_code"], S["A1_food"], S["A1_gap"])}
    real = {(p, int(q)): (a, b) for p, q, a, b in zip(Lb["province_code"], Lb["q"], Lb["mf"], Lb["mg"])}
    ef, eg = [], []
    for t, k, p in zip(S["t"], S["lead"], S["province_code"]):
        t, k = int(t), int(k)
        pr, rl = proj.get((t - 1 - k, k, p)), real.get((p, t - 1))
        if pr is None or rl is None:
            ef.append(np.nan), eg.append(np.nan)
        else:
            ef.append(rl[0] - pr[0]), eg.append(rl[1] - pr[1])
    S = S.copy()
    S["EF_recent"], S["EG_recent"] = ef, eg
    return S


def dev_rule(b, x):
    return {"1a_L2_dev_brier_gain_ge_0.005": b[2]["dev"]["brier"] - x[2]["dev"]["brier"] >= .005,
            "1c_L2_dev_balanced_not_lower": x[2]["dev"]["balanced_accuracy"] >= b[2]["dev"]["balanced_accuracy"] - 1e-12,
            "1b_L1_dev_brier_not_worse_by_0.005": x[1]["dev"]["brier"] <= b[1]["dev"]["brier"] + .005}


def main():
    proto = T.LT / "PROTOCOL_LEAD2_BIAS_TRACK.md"
    assert T.sha256(proto) == (T.HERE / "BIAS_TRACK_SHA256.txt").read_text().strip(), "protocol changed after freezing"
    E = pd.read_csv(T.OUT / "asof_reeval_rows.csv", dtype={"province_code": str})
    C = pd.read_csv(T.OUT / "asof_reeval_cutoffs.csv", dtype={"province_code": str})
    Lb = RCII.labels()
    origins = sorted(E["t"].unique())
    res = {"protocol_sha256": T.sha256(proto)}
    S0 = add_recent(T.stack(), Lb)
    SV = add_recent(A.scenario_stack(C, "VER"), Lb)
    res["coverage_lead2"] = {c: float(S0.loc[S0["lead"] == 2, c].notna().mean()) for c in NEW}
    # availability: the realised quarter t-1 and the earlier projection both precede the issue
    assert ((S0["t"] - 1) < S0["t"]).all()
    for name, S, base in (("X1", S0, T.U2), ("X1VER", SV, T.U2)):
        P = T.run(base + NEW, origins, S=S).rename(columns={"pi_P": f"{name}_price"})
        E = E.merge(P[KEY + [f"{name}_price"]], on=KEY, how="left")
        E[f"{name}_p"] = E["pi_H_AB"] * E[f"{name}_price"]
        print(name, "fitted", flush=True)
    cands = ["P0H4", "B0", "CRVER", "CRANCVER", "CRANCD10", "X1", "X1VER"]
    ev = {c: FN.lead_eval(E, c) for c in cands}
    res["development_selection"] = {"X1_vs_B0": dev_rule(ev["B0"]["leads"], ev["X1"]["leads"]),
                                    "X1VER_vs_CRVER": dev_rule(ev["CRVER"]["leads"], ev["X1VER"]["leads"]),
                                    "dev_L2_brier": {c: ev[c]["leads"][2]["dev"]["brier"] for c in cands},
                                    "dev_L2_balanced": {c: ev[c]["leads"][2]["dev"]["balanced_accuracy"] for c in cands},
                                    "dev_L1_brier": {c: ev[c]["leads"][1]["dev"]["brier"] for c in cands}}
    res["development_candidate"] = [c for c, r in (("X1", res["development_selection"]["X1_vs_B0"]),
                                                    ("X1VER", res["development_selection"]["X1VER_vs_CRVER"])) if all(r.values())]
    res["results"] = {c: {k: A.summ(ev[c], k) for k in (1, 2)} | {"max_reliable_lead": ev[c]["max_reliable_lead"]} for c in cands}
    res["adoption_vs_B0"] = {c: [k for k, v in FN.adoption_rule(ev["B0"]["leads"], ev[c]["leads"]).items() if not v] for c in ("X1", "X1VER")}
    g2 = E[E["lead"] == 2]
    res["calibration_lead2"] = {c: RC.calib(g2["y"], g2[f"{c}_p"]) for c in cands}
    res["cluster_lead2"] = {c: RCII.cluster_stats(g2, c) for c in ("X1", "X1VER")}
    res["parts_lead2"] = {c: A.parts(g2, f"{c}_price") for c in ("X1", "X1VER")}
    res["predicted_high_rate_lead2"] = {c: float((g2[f"{c}_p"] >= .5).mean()) for c in cands}
    res["by_quarter_errors_lead2"] = {c: {F.qs(int(q)): int(((h[f"{c}_p"] >= .5).astype(int) != h["y"]).sum()) for q, h in g2.groupby("q")} for c in ("B0", "X1", "X1VER")}
    res["by_province_accuracy_lead2"] = {c: {A.NAMES[p]: float(((h[f"{c}_p"] >= .5).astype(int) == h["y"]).mean()) for p, h in g2.groupby("province_code")} for c in ("B0", "X1", "X1VER")}
    E.to_csv(T.OUT / "bias_track_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    (T.OUT / "bias_track.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res["development_selection"], indent=1, default=float))
    for c in cands:
        r = res["results"][c][2]
        print(c, round(r["accuracy"], 3), round(r["balanced_accuracy"], 3), round(r["precision"], 3), round(r["recall"], 3),
              round(r["brier"], 4), r["failed"], "L1", res["results"][c][1]["failed"])


if __name__ == "__main__":
    sys.exit(main())
