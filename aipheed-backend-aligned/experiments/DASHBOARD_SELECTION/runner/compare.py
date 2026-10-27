"""Four-candidate comparison on matched rows (Main, S3, P0H4, FIRI v2) + baselines and the Chapter-I comparators.

Main serves FIRI v2 (git show main:backend/Dockerfile; no ch1_system on main) and its FIRI v2 history file is identical to
the current branch's (same commit 2b1f65a), so Main and FIRI v2 give the same forecasts; FIRI v2 is a Lead-2 index only
(target = origin + 2) and not a probability.

    python compare.py   # out/comparison.json, out/quarter_table_lead1.csv, out/quarter_table_lead2.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
ROOT = EXP.parents[1]
OUT = HERE.parent / "out"
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))
import l2_lib as X  # noqa: E402

FM, L, C = X.FM, X.L, X.C
PROB = {"S3 (single LightGBM)": "C_p", "P0H4 (served hybrid)": "P0H4_p3"}
BASE = {"always-LOW": "ALWAYS-LOW_p", "PERSIST-SI (naive persistence)": "PERSIST-SI_p", "climatology": "CLIM_p"}
COMP = {"LR-COMB (logistic, combined)": "LR-COMB_p", "LR-GOV (logistic, PSA/government only)": "LR-GOV_p",
        "LR-NLP (logistic, news only)": "LR-NLP_p", "LGBM-GOV (LightGBM, government only)": "LGBM-GOV_p",
        "LGBM-NLP (LightGBM, news only)": "LGBM-NLP_p", "CH1-LGBM (per-lead, earlier)": "CH1_p"}


def qs(q):
    return f"{int(q) // 4}-Q{int(q) % 4 + 1}"


def metrics(g: pd.DataFrame, col: str, prob: bool = True) -> dict:
    y = g["y"].astype(int).to_numpy()
    p = g[col].to_numpy(float)
    yh = (p >= 0.5).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    rec, spec = tp / max(tp + fn, 1), tn / max(tn + fp, 1)
    prec = tp / (tp + fp) if tp + fp else None
    two = len(set(y.tolist())) == 2 and len(set(p.tolist())) > 1
    hq = C.bl_quarters()
    lab = C.labels().set_index(["province_code", "q"])["y"]
    ons = g[[lab.get((pp, q - 1), None) == 0 and yy == 1 for pp, q, yy in zip(g["province_code"], g["q"], g["y"])]]
    rising = g[[hq.get(q, np.nan) > hq.get(q - 1, np.nan) for q in g["q"]]]
    pre, post = g[g["q"] < L.qi("2025-Q2")], g[g["q"] >= L.qi("2025-Q2")]
    acc_q = {qs(q): float(((h[col] >= .5).astype(int) == h["y"]).mean()) for q, h in g.groupby("q")}
    loqo = [float(((g[g["q"] != q][col] >= .5).astype(int) == g[g["q"] != q]["y"]).mean()) for q in g["q"].unique()]
    rng = np.random.default_rng(2036)
    uq = g["q"].unique()
    corr = ((g[col] >= .5).astype(int) == g["y"]).to_numpy(float)
    by = {q: corr[g["q"].to_numpy() == q] for q in uq}
    bs = [np.concatenate([by[q] for q in rng.choice(uq, len(uq))]).mean() for _ in range(2000)]

    def acc(h):
        return float(((h[col] >= .5).astype(int) == h["y"]).mean()) if len(h) else None
    return {"rows": int(len(g)), "quarters": int(g["q"].nunique()), "high": int(y.sum()),
            "accuracy": f"{tp + tn}/{len(y)} = {(tp + tn) / len(y):.3f}", "acc": (tp + tn) / len(y),
            "acc_ci90": [float(np.quantile(bs, .05)), float(np.quantile(bs, .95))],
            "balanced": (rec + spec) / 2, "precision": prec, "recall": f"{tp}/{tp + fn} = {rec:.3f}", "rec": rec,
            "f1": 2 * prec * rec / (prec + rec) if prec and rec else 0.0, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "brier": float(np.mean((p - y) ** 2)) if prob else None,
            "auc": float(roc_auc_score(y, p)) if two else None, "pr_auc": float(average_precision_score(y, p)) if two else None,
            "onsets_caught": f"{int((ons[col] >= .5).sum())}/{len(ons)}",
            "rising_acc": acc(rising), "pre_2025Q2_acc": acc(pre), "post_2025Q2_acc": acc(post),
            "pre_recall": f"{int(((pre[col] >= .5) & (pre['y'] == 1)).sum())}/{int(pre['y'].sum())}",
            "post_recall": f"{int(((post[col] >= .5) & (post['y'] == 1)).sum())}/{int(post['y'].sum())}",
            "loqo_min": min(loqo), "acc_by_quarter": acc_q, "quarters_below_0.6": sum(v < .6 for v in acc_q.values())}


def main():
    X.U.setup()
    D = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    comp = []
    for k in (1, 2):
        v = pd.read_csv(EXP / "FINAL_VERIFICATION" / "out" / f"horizon_predictions_lead{k}.csv", dtype={"province_code": str})
        comp.append(v[["t", "lead", "province_code"] + [c for c in COMP.values()]])
    D = D.merge(pd.concat(comp), on=["t", "lead", "province_code"], how="left")
    fi = pd.read_csv(ROOT / "backend" / "data" / "thesis" / "firi2_history.csv", dtype={"province_code": str})
    fi = fi[fi["kind"] == "backtest"].assign(q=lambda d: d["target"].map(L.qi), t=lambda d: d["origin_quarter"].map(L.qi))
    D = D.merge(fi[["province_code", "q", "t", "FIRI"]].assign(lead=2), on=["province_code", "q", "t", "lead"], how="left")
    D["price_only_p"] = D["P0_price"]
    D["hunger_only_p"] = (D["h_last"] > X.H_LINE).astype(float)
    out = {"rows": {}, "leads": {}}
    for k in (1, 2):
        g = D[D["lead"] == k]
        res = {}
        for name, col in {**PROB, **BASE, **COMP, "price-only diagnostic (pi_P)": "price_only_p",
                          "hunger-only (latest SWS > 11.3)": "hunger_only_p"}.items():
            if g[col].notna().all():
                res[name] = metrics(g, col, prob=True)
            else:
                res[name] = {"note": f"not available on all {len(g)} rows ({int(g[col].notna().sum())} available)"}
        if k == 2:
            gf = g[g["FIRI"].notna()]
            res["Main = FIRI v2 (index, HIGH at 0.50)"] = {**metrics(gf, "FIRI", prob=False),
                                                           "matched_rows_note": f"{len(gf)} of {len(g)} Lead-2 rows have a FIRI value"}
            if len(gf) < len(g):
                sub = g[g["FIRI"].notna()]
                res["S3 on FIRI's rows"] = metrics(sub, "C_p")
                res["P0H4 on FIRI's rows"] = metrics(sub, "P0H4_p3")
        else:
            res["Main = FIRI v2 (index, HIGH at 0.50)"] = {"note": "not applicable: FIRI v2 has no Lead-1 history (Lead-2 index)"}
        y = g["y"].astype(int).to_numpy()
        t = FM.boot_diff(g, (g["C_p"] - y) ** 2, (g["P0H4_p3"] - y) ** 2)
        res["brier_S3_minus_P0H4"] = {"diff": t["diff"], "ci90": t["ci90"], "p_two": t["p_two"]}
        out["leads"][k] = res
        qt = g.groupby("q").agg(high=("y", "sum"), rows=("y", "size"), S3_mean=("C_p", "mean"), P0H4_mean=("P0H4_p3", "mean"),
                                FIRI_mean=("FIRI", "mean"), hunger=("hunger", "first"), H=("H", "first"))
        for name, col in (("S3", "C_p"), ("P0H4", "P0H4_p3"), ("FIRI", "FIRI")):
            qt[f"{name}_TP/FP"] = [f"{int(((h[col] >= .5) & (h['y'] == 1)).sum())}/{int(((h[col] >= .5) & (h['y'] == 0)).sum())}"
                                   if h[col].notna().all() else "n/a" for _, h in g.groupby("q")]
        qt.index = [qs(q) for q in qt.index]
        qt.round(3).to_csv(OUT / f"quarter_table_lead{k}.csv", lineterminator="\n")
        print(f"\n==== Lead {k} ({len(g)} rows, {g['q'].nunique()} quarters, {int(g['y'].sum())} HIGH)")
        for n, m in res.items():
            if "acc" in m:
                print(f"{n:42s} acc {m['accuracy']:16s} bal {m['balanced']:.3f} P {m['precision'] if m['precision'] is None else round(m['precision'], 2)} "
                      f"R {m['recall']:14s} F1 {m['f1']:.2f} FN {m['fn']:2d} FP {m['fp']:2d} Brier {m['brier'] if m['brier'] is None else round(m['brier'], 3)} "
                      f"AUC {m['auc'] if m['auc'] is None else round(m['auc'], 2)} onsets {m['onsets_caught']} pre/post {m['pre_2025Q2_acc']:.2f}/{m['post_2025Q2_acc']:.2f} "
                      f"loqo {m['loqo_min']:.2f} q<0.6 {m['quarters_below_0.6']}")
            elif "note" in m:
                print(f"{n:42s} {m['note']}")
        print("Brier S3-P0H4", res["brier_S3_minus_P0H4"])
    FM.write_json(OUT / "comparison.json", out)


if __name__ == "__main__":
    main()
