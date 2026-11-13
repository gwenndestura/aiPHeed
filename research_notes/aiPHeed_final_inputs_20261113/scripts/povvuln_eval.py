r"""Scores PROTOCOL_POVVULN (sha bb63c891) exactly as locked: arms P0, P1-P3, P1F-P3F against P0 (contribution of the added group)
and against B0 (FINAL as sealed). Labels from ETMIX_rows_all_leads.csv. Run: python -I povvuln_eval.py"""
import glob
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, roc_auc_score

HERE = Path(__file__).resolve().parents[1]; EV = HERE / "evidence"; RN = HERE.parent
K = ["key", "survey", "lead"]
ARMS = ["B0", "P0", "P1", "P2", "P3", "P1F", "P2F", "P3F"]
REF = pd.read_csv(RN / "aiPHeed_final_etmix_20261113" / "evidence" / "ETMIX_rows_all_leads.csv")
REF = REF[REF.lead.isin([1, 2])][K + ["y_high", "FINAL"]]
P = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts" / "*.csv"))], ignore_index=True)
P = P[P.arm.isin(ARMS)]
rng = np.random.default_rng(20261113)


def metrics(y, p):
    yh = (p >= 0.5).astype(int)
    tp, fp, fn, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    return {"n": len(y), "TP": tp, "FP": fp, "FN": fn, "TN": tn, "pred_high_share": round(float(yh.mean()), 4), "accuracy": round((tp + tn) / len(y), 4),
            "precision_high": round(tp / (tp + fp), 4) if tp + fp else np.nan, "recall_high": round(tp / (tp + fn), 4) if tp + fn else np.nan,
            "f1_high": round(f1_score(y, yh, zero_division=0), 4) if y.sum() else np.nan,
            "auc": round(roc_auc_score(y, p), 4) if 0 < y.sum() < len(y) else np.nan, "brier": round(float(((p - y) ** 2).mean()), 4),
            "logloss": round(float(-(y * np.log(pc) + (1 - y) * np.log(1 - pc)).mean()), 4)}


def owner(m):
    return all(pd.notna(m[k]) and m[k] >= 0.75 for k in ("accuracy", "precision_high", "recall_high", "f1_high", "auc"))


D = P.merge(REF, on=K)
assert D.groupby(["arm", "lead", "seed"]).size().nunique() == 1
M = D.groupby(["arm"] + K, as_index=False).agg(p=("p", "mean"), y=("y_high", "first"))
rows = []
for (a, L), g in M.groupby(["arm", "lead"]):
    for s, x in list(g.groupby("survey")) + [("POOLED", g)]:
        m = metrics(x.y.values, x.p.values); rows.append({"arm": a, "lead": L, "round": s, "agg": "seed_mean", **m, "owner_5_pass": owner(m)})
for (a, L, sd), g in D.groupby(["arm", "lead", "seed"]):
    m = metrics(g.y_high.values, g.p.values); rows.append({"arm": a, "lead": L, "round": "POOLED", "agg": f"seed_{sd}", **m, "owner_5_pass": owner(m)})
T = pd.DataFrame(rows); T["arm"] = pd.Categorical(T.arm, ARMS); T = T.sort_values(["lead", "arm", "agg", "round"])
T.to_csv(EV / "POVVULN_metrics.csv", index=False, lineterminator="\n")

inc = []
for base in ("P0", "B0"):
    for L in (1, 2):
        b = M[(M.arm == base) & (M.lead == L)].set_index(["key", "survey"])
        y = b.y.values
        for a in ARMS:
            if a == base:
                continue
            x = M[(M.arm == a) & (M.lead == L)].set_index(["key", "survey"]).reindex(b.index)
            d = (x.p.values - y) ** 2 - (b.p.values - y) ** 2
            bs = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(3000)])
            inc.append({"vs": base, "lead": L, "arm": a, "dBrier": round(float(d.mean()), 4), "ci95_lo": round(float(np.percentile(bs, 2.5)), 4),
                        "ci95_hi": round(float(np.percentile(bs, 97.5)), 4),
                        "by_round": {s: round(float(d[b.index.get_level_values("survey") == s].mean()), 4) for s in sorted(set(b.index.get_level_values("survey")))}})
I = pd.DataFrame(inc); I.to_csv(EV / "POVVULN_incremental.csv", index=False, lineterminator="\n")

FEATS = ["pv_fam", "pv_pop", "sb_fam", "sb_pop", "d_pv_pop", "d_pv_fam", "p_poverty_gap", "p_density_c", "p_popgrowth", "p_poverty", "p_subsistence", "p_density"]
fits = P.drop_duplicates(["arm", "survey", "lead", "seed"])
S = pd.DataFrame([{"arm": a, "lead": L, "fits": len(g), **{c: int(g.selected.fillna("").str.split(";").map(lambda s: c in s).sum()) for c in FEATS}}
                  for (a, L), g in fits.groupby(["arm", "lead"])])
S.to_csv(EV / "POVVULN_selection_counts.csv", index=False, lineterminator="\n")

sm = T[T["agg"] == "seed_mean"]
dec = []
for a in ARMS[1:]:
    ok, why = True, []
    for L in (1, 2):
        A = sm[(sm.arm == a) & (sm.lead == L)].set_index("round"); B = sm[(sm.arm == "B0") & (sm.lead == L)].set_index("round")
        rr = [r for r in A.index if r != "POOLED"]
        for c, t in ((bool(A.at["POOLED", "owner_5_pass"]), "pooled owner metrics"), (A.at["POOLED", "brier"] <= B.at["POOLED", "brier"] + 0.005, "pooled Brier"),
                     (all(pd.isna(B.at[r, "recall_high"]) or A.at[r, "recall_high"] >= B.at[r, "recall_high"] for r in rr), "no round loses HIGH recall"),
                     (any(pd.notna(B.at[r, "f1_high"]) and A.at[r, "f1_high"] > B.at[r, "f1_high"] for r in rr), "a round gains HIGH F1")):
            if not c:
                ok = False; why.append(f"L{L}: fails {t}")
    ll = sm[(sm.arm == a) & (sm.lead == 1) & (sm["round"].isin(["ENNS2018", "ENNS2019"]))]
    dec.append({"arm": a, "meets_1_to_3": ok, "reasons": "; ".join(why) or "-", "logloss_2018_2019_L1": round(float((ll.logloss * ll.n).sum() / ll.n.sum()), 4)})
DEC = pd.DataFrame(dec)
win = DEC[DEC.meets_1_to_3].sort_values("logloss_2018_2019_L1")
DEC["decision"] = DEC.arm.map(lambda a: "REPLACES FINAL" if len(win) and a == win.arm.iloc[0] else "not adopted")
DEC.to_csv(EV / "POVVULN_decision.csv", index=False, lineterminator="\n")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(sm[["arm", "lead", "round", "TP", "FP", "FN", "TN", "accuracy", "precision_high", "recall_high", "f1_high", "auc", "brier", "owner_5_pass"]].to_string(index=False))
print(I.to_string(index=False)); print(S.to_string(index=False)); print(DEC.to_string(index=False))
