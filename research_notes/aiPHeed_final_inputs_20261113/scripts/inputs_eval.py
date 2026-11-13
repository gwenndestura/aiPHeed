r"""Scores the PROTOCOL_INPUTS arms (sha 4cb830c6) exactly as locked. Labels and FINAL's stored fold predictions from
aiPHeed_final_etmix_20261113/evidence/ETMIX_rows_all_leads.csv (column FINAL). Run: python -I inputs_eval.py"""
import glob
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, roc_auc_score

HERE = Path(__file__).resolve().parents[1]; EV = HERE / "evidence"; EV.mkdir(exist_ok=True)
RN = HERE.parent
K = ["key", "survey", "lead"]
REF = pd.read_csv(RN / "aiPHeed_final_etmix_20261113" / "evidence" / "ETMIX_rows_all_leads.csv")
REF = REF[REF.lead.isin([1, 2])][K + ["province", "region", "y_high", "FINAL"]]
P = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts" / "*.csv"))], ignore_index=True)
ARMS = ["B0", "D-ALL", "D-POV", "D-DEN", "D-GRDP", "D-ONI", "F-ALL", "N-OFF", "N-OFF-F", "N-AFF", "N-ALL", "N-ALL-F"]
rng = np.random.default_rng(20261113)


def metrics(y, p):
    yh = (p >= 0.5).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    eps = 1e-6; pc = np.clip(p, eps, 1 - eps)
    return {"n": len(y), "TP": tp, "FP": fp, "FN": fn, "TN": tn, "pred_high_share": round(float(yh.mean()), 4),
            "accuracy": round((tp + tn) / len(y), 4),
            "precision_high": round(tp / (tp + fp), 4) if tp + fp else np.nan, "recall_high": round(tp / (tp + fn), 4) if tp + fn else np.nan,
            "f1_high": round(f1_score(y, yh, zero_division=0), 4) if y.sum() else np.nan,
            "precision_low": round(tn / (tn + fn), 4) if tn + fn else np.nan, "recall_low": round(tn / (tn + fp), 4) if tn + fp else np.nan,
            "auc": round(roc_auc_score(y, p), 4) if 0 < y.sum() < len(y) else np.nan,
            "brier": round(float(((p - y) ** 2).mean()), 4), "logloss": round(float(-(y * np.log(pc) + (1 - y) * np.log(1 - pc)).mean()), 4)}


def owner_pass(m):
    return all(pd.notna(m[k]) and m[k] >= 0.75 for k in ("accuracy", "precision_high", "recall_high", "f1_high", "auc"))


# ---- seed mean and per seed
D = P.merge(REF, on=K, how="inner")
assert D.groupby(["arm", "lead", "seed"]).size().nunique() == 1, "unequal rows per arm/lead/seed"
M = D.groupby(["arm"] + K, as_index=False).agg(p=("p", "mean"), y=("y_high", "first"), FINAL=("FINAL", "first"), n_seeds=("seed", "nunique"))

# ---- reproduction check
b0 = M[M.arm == "B0"]
rep = float((b0.p - b0.FINAL).abs().max())
print(f"B0 vs stored FINAL: max |dp| = {rep:.2e} over {len(b0)} rows", "OK" if rep <= 1e-6 else "MISMATCH")

rows = []
for (arm, lead), g in M.groupby(["arm", "lead"]):
    for s, x in list(g.groupby("survey")) + [("POOLED", g)]:
        m = metrics(x.y.values, x.p.values)
        rows.append({"arm": arm, "lead": lead, "round": s, "agg": "seed_mean", **m, "owner_5_pass": owner_pass(m)})
for (arm, lead, seed), g in D.groupby(["arm", "lead", "seed"]):
    m = metrics(g.y_high.values, g.p.values)
    rows.append({"arm": arm, "lead": lead, "round": "POOLED", "agg": f"seed_{seed}", **m, "owner_5_pass": owner_pass(m)})
T = pd.DataFrame(rows)
T["arm"] = pd.Categorical(T.arm, ARMS); T = T.sort_values(["lead", "arm", "agg", "round"])
T.to_csv(EV / "INPUTS_metrics.csv", index=False, lineterminator="\n")

# ---- paired bootstrap vs B0 (province-round rows), seed-mean probabilities
inc = []
for lead in (1, 2):
    base = M[(M.arm == "B0") & (M.lead == lead)].set_index(["key", "survey"])
    for arm in ARMS[1:]:
        a = M[(M.arm == arm) & (M.lead == lead)].set_index(["key", "survey"]).reindex(base.index)
        y = base.y.values
        for name, f in (("brier", lambda p: (p - y) ** 2), ("logloss", lambda p: -(y * np.log(np.clip(p, 1e-6, 1 - 1e-6)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1)))))):
            d = f(a.p.values) - f(base.p.values)
            bs = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(3000)])
            inc.append({"lead": lead, "arm": arm, "metric": name, "delta_vs_B0": round(float(d.mean()), 4),
                        "ci95_lo": round(float(np.percentile(bs, 2.5)), 4), "ci95_hi": round(float(np.percentile(bs, 97.5)), 4),
                        "by_round": {s: round(float(d[(base.index.get_level_values("survey") == s)].mean()), 4) for s in sorted(set(base.index.get_level_values("survey")))}})
I = pd.DataFrame(inc); I.to_csv(EV / "INPUTS_incremental_vs_B0.csv", index=False, lineterminator="\n")

# ---- selection frequency of the official columns
OFF = ["aff_g", "aff_share", "p_poverty", "p_subsistence", "p_poverty_gap", "p_density", "p_density_c", "p_popgrowth", "hh_grdp_g", "hh_grdp_rel",
       "oni", "oni_12m", "oni_max12", "nino_m12", "nina_m12", "oni_lag2q"]
fits = P.drop_duplicates(["arm", "survey", "lead", "seed"])
S = pd.DataFrame([{"arm": a, "lead": L, "fits": len(g), **{c: int(g.selected.fillna("").str.split(";").map(lambda s: c in s).sum()) for c in OFF}}
                  for (a, L), g in fits.groupby(["arm", "lead"])])
S.to_csv(EV / "INPUTS_selection_counts.csv", index=False, lineterminator="\n")

# ---- decision rule
dec = []
sm = T[T.agg == "seed_mean"]
for arm in ARMS[1:]:
    ok, why = True, []
    for lead in (1, 2):
        A = sm[(sm.arm == arm) & (sm.lead == lead)].set_index("round"); B = sm[(sm.arm == "B0") & (sm.lead == lead)].set_index("round")
        c1 = bool(A.at["POOLED", "owner_5_pass"]); c2 = A.at["POOLED", "brier"] <= B.at["POOLED", "brier"] + 0.005
        rr = [r for r in A.index if r != "POOLED"]
        c3a = all((pd.isna(B.at[r, "recall_high"])) or A.at[r, "recall_high"] >= B.at[r, "recall_high"] for r in rr)
        c3b = any(pd.notna(B.at[r, "f1_high"]) and A.at[r, "f1_high"] > B.at[r, "f1_high"] for r in rr)
        for c, t in ((c1, "pooled owner metrics"), (c2, "pooled Brier"), (c3a, "no round loses HIGH recall"), (c3b, "a round gains HIGH F1")):
            if not c:
                ok = False; why.append(f"L{lead}: fails {t}")
    ll = sm[(sm.arm == arm) & (sm.lead == 1) & (sm["round"].isin(["ENNS2018", "ENNS2019"]))]
    dec.append({"arm": arm, "meets_1_to_3": ok, "reasons": "; ".join(why) or "-", "logloss_2018_2019_L1": round(float((ll.logloss * ll.n).sum() / ll.n.sum()), 4)})
DEC = pd.DataFrame(dec)
win = DEC[DEC.meets_1_to_3].sort_values("logloss_2018_2019_L1")
DEC["decision"] = DEC.arm.map(lambda a: "REPLACES FINAL" if len(win) and a == win.arm.iloc[0] else "not adopted")
DEC.to_csv(EV / "INPUTS_decision.csv", index=False, lineterminator="\n")

pd.set_option("display.width", 260); pd.set_option("display.max_columns", 30)
cols = ["arm", "lead", "round", "TP", "FP", "FN", "TN", "accuracy", "precision_high", "recall_high", "f1_high", "auc", "brier", "owner_5_pass"]
print(sm[cols].to_string(index=False))
print(I[I.metric == "brier"].to_string(index=False))
print(S.to_string(index=False))
print(DEC.to_string(index=False))
