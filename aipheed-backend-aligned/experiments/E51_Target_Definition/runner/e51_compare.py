"""E51 single run under the frozen PROTOCOL.md: temporal prevalence and defensibility criteria of six candidate targets;
Lead-2 chronological comparison per target (E38 LightGBM procedure, logistic regression, persistence, always-HIGH/LOW,
E46 where its target permits); reproductions of E36/E38/E46. Runs inside the E32 data guard; writes confined to E51.

    backend/venv/Scripts/python.exe -B runner/e51_compare.py   -> runs/<UTC stamp>/{results.json, rows_<target>.csv}
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E51 = Path(__file__).resolve().parents[1]
EXP = E51.parent
sys.path.insert(0, str(EXP / "E38_Lead2_Diagnosis_Tuning" / "runner"))
import e38_lib as E  # noqa: E402  (installs the E32 guard)

E.L7.L6.guard32.EXP = E51
np, pd, qk, qs, PROVS, L6 = E.np, E.pd, E.qk, E.qs, E.PROVS, E.L6
K2 = 2
RUN36 = EXP / "E36_LightGBM_One_Quarter_Ahead" / "runs" / "20261015T023921Z" / "predictions.csv"
RUN38 = EXP / "E38_Lead2_Diagnosis_Tuning" / "runs" / "20261015T033922Z" / "predictions.csv"
RUN7 = EXP / "E46_Rice_Policy" / "runs" / "i7_20261017T000111Z" / "predictions_i7.csv"
TARGETS = ["EQ3-G", "EQ3-T", "T43", "PS", "RQ", "YW"]
NEEDS_SWS = {"EQ3-G": True, "EQ3-T": True, "T43": True, "PS": False, "RQ": False, "YW": True}
AS_OF = {"EQ3-G": False, "EQ3-T": True, "T43": True, "PS": True, "RQ": True, "YW": True}   # C4 by definition


def verify() -> str:
    want = (E51 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E51 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


class DataLabel(E.Data):
    """E38 data with every label (training targets, y_last, prior rate, evaluation) replaced by a fixed target label."""

    def __init__(self, lab: dict, pers: dict):
        super().__init__()
        self.lab, self.pers = lab, pers

    def label(self, p, target, t):
        return self.lab.get((p, target))

    def features(self, t, k):
        X = super().features(t, k).copy()
        X["y_last"] = [self.pers.get((t, p), np.nan) for p in X["province_code"]]
        return X

    def training_pairs(self, t, k):
        tr = super().training_pairs(t, k)
        if tr.empty:
            return tr
        tr = tr.copy()
        tr["y"] = [self.lab.get((p, q)) for p, q in zip(tr["province_code"], tr["target_q"])]
        return tr.dropna(subset=["y"]).astype({"y": int}).reset_index(drop=True)


def metrics(y, yhat, p):
    from sklearn.metrics import roc_auc_score
    y, yhat, p = np.asarray(y, int), np.asarray(yhat, int), np.asarray(p, float)
    tp, tn = int(((yhat == 1) & (y == 1)).sum()), int(((yhat == 0) & (y == 0)).sum())
    fp, fn = int(((yhat == 1) & (y == 0)).sum()), int(((yhat == 0) & (y == 1)).sum())
    rh = tp / (tp + fn) if tp + fn else None
    rl = tn / (tn + fp) if tn + fp else None
    pr = tp / (tp + fp) if tp + fp else None
    return {"n": int(len(y)), "accuracy": float((y == yhat).mean()),
            "balanced_accuracy": None if rh is None or rl is None else (rh + rl) / 2, "recall_HIGH": rh, "recall_LOW": rl,
            "precision_HIGH": pr, "f1_HIGH": (2 * pr * rh / (pr + rh)) if pr and rh else None,
            "brier": float(np.mean((p - y) ** 2)),
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(p)) > 1 else None,
            "confusion": {"TP": tp, "TN": tn, "FP": fp, "FN": fn}, "share_HIGH_calls": float(yhat.mean())}


def block(df, arms):
    rng = np.random.default_rng(51)
    out = {}
    qs_ = df["target"].unique()
    for a in arms:
        m = metrics(df["y"], df[f"{a}_yhat"], df[f"{a}_p"])
        vals = [float(np.mean(np.concatenate([(df[df["target"] == q][f"{a}_yhat"] == df[df["target"] == q]["y"]).to_numpy()
                                              for q in rng.choice(qs_, len(qs_))]))) for _ in range(1000)]
        m["accuracy_ci95"] = [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]
        m["by_quarter"] = {q: float((g[f"{a}_yhat"] == g["y"]).mean()) for q, g in df.groupby("target")}
        out[a] = m
    return out


def within_share(lab: dict) -> float | None:
    s = pd.Series(lab).rename("y").reset_index()
    s.columns = ["p", "q", "y"]
    v = s["y"].astype(float)
    if v.var() == 0:
        return None
    w = s.assign(v=v).groupby("q")["v"].transform(lambda x: x - x.mean())
    return float((w ** 2).sum() / ((v - v.mean()) ** 2).sum())


def accepted(m, base) -> bool:
    return (m["accuracy"] >= 0.75 and (m["balanced_accuracy"] or 0) >= 0.70 and (m["recall_HIGH"] or 0) >= 0.60
            and (m["recall_LOW"] or 0) >= 0.60 and all(m["brier"] < base[b]["brier"] for b in ("PERSIST", "HIGH", "LOW")))


def main():
    proto = verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E51 / "runs" / stamp
    out.mkdir(parents=True)
    d0 = E.Data()
    S1 = {k: v for k, v in d0.Sv.items() if v == v}
    D = {k: v for k, v in d0.Dm.items() if v == v}
    cpi = pd.read_csv(E51 / "data" / "labels_cpi.csv", dtype={"province_code": str})
    pcpi = pd.read_csv(E51 / "data" / "persistence_cpi.csv", dtype={"province_code": str})
    med = float(np.median(list(S1.values())))
    labels = {"EQ3-G": {k: int(v > med) for k, v in S1.items()},
              "T43": {(p, int(q)): int(y) for p, q, y in zip(cpi["province_code"], cpi["q"], cpi["T43"]) if y == y},
              "PS": {(p, int(q)): int(y) for p, q, y in zip(cpi["province_code"], cpi["q"], cpi["PS"])}}
    rq = {}
    for q in sorted({q for _, q in D}):
        vals = {p: D.get((p, q)) for p in PROVS}
        if all(v is not None for v in vals.values()):
            m_ = float(np.median(list(vals.values())))
            rq.update({(p, q): int(v > m_) for p, v in vals.items()})
    labels["RQ"] = rq
    labels["YW"] = {(p, q): int(s > S1[(p, q - 4)]) for (p, q), s in S1.items() if (p, q - 4) in S1}
    # EQ3-T labels depend on the origin; for prevalence use each quarter's tau at its own publication (t = q + 1)
    labels["EQ3-T_prev"] = {(p, q): int(s > d0.tau(q + 1)) for (p, q), s in S1.items() if q + 1 <= qk("2026-Q3")}

    def persistence(name, t):
        if name == "T43":
            return {r.province_code: r.T43_last for r in pcpi[pcpi["t"] == t].itertuples()}
        if name == "PS":
            return {r.province_code: r.PS_last for r in pcpi[pcpi["t"] == t].itertuples()}
        lab = labels[name]
        if NEEDS_SWS[name]:
            cand = [q for q in d0.posted_quarters(E.L7.origin(t)) if q <= t - 1]
        else:
            cand = [q for q in range(qk("2021-Q1"), t)]
        outp = {}
        for p in PROVS:
            qq = [q for q in cand if (p, q) in lab]
            outp[p] = lab[(p, qq[-1])] if qq else None
        return outp

    res = {"protocol_sha256": proto, "run_utc": stamp, "global_median_S1": med,
           "evidence_status": "DEVELOPMENT evidence; no unseen quarter (PROTOCOL 0)."}
    # ---------------- prevalence and criteria
    prev = {}
    for name in ["EQ3-G", "EQ3-T_prev", "T43", "PS", "RQ", "YW"]:
        lab = labels[name]
        by = {}
        for (p, q), y in lab.items():
            yr = qs(q)[:4]
            by.setdefault(yr, [0, 0])
            by[yr][0] += 1
            by[yr][1] += y
        rec = [y for (p, q), y in lab.items() if qk("2024-Q1") <= q <= qk("2026-Q4")]
        prev[name.replace("_prev", "")] = {"by_year": {k: {"rows": v[0], "HIGH": v[1], "share": round(v[1] / v[0], 3)} for k, v in sorted(by.items())},
                                           "share_HIGH_2024_2026": round(float(np.mean(rec)), 3) if rec else None,
                                           "within_quarter_variance_share": within_share(lab)}
    res["prevalence"] = prev
    # ---------------- reproductions
    p36 = pd.read_csv(RUN36, dtype={"province_code": str})
    res["reproduce"] = {}
    for arm in ("E36-LGBM", "B1_PERSISTENCE", "ALWAYS_HIGH"):
        g = p36[p36["arm"] == arm]
        res["reproduce"][f"E36 lead1 {arm}"] = metrics(g["y"], (g["p"] >= 0.5).astype(int), g["p"])
    p38 = pd.read_csv(RUN38, dtype={"province_code": str})
    for arm in ("E38-LGBM", "B1_PERSISTENCE", "ALWAYS_HIGH"):
        g = p38[p38["arm"] == arm]
        thr = g["threshold"] if arm == "E38-LGBM" else 0.5
        res["reproduce"][f"E38 lead2 {arm}"] = metrics(g["y"], (g["p"] >= thr).astype(int), g["p"])
    P7 = pd.read_csv(RUN7, dtype={"province_code": str})
    P7["target"] = (P7["t"] + 2).map(qs)
    # ---------------- per-target chronological comparison
    res["targets"] = {}
    for name in ["EQ3-T", "EQ3-G", "T43", "PS", "RQ", "YW"]:
        if name == "EQ3-T":
            dl = d0
        else:
            pers_all = {}
            for t in range(qk("2021-Q2"), qk("2026-Q3") + 1):
                for p, v in persistence(name, t).items():
                    pers_all[(t, p)] = np.nan if v is None or v != v else float(v)
            dl = DataLabel(labels[name], pers_all)
        Pr, info = E.walk_forward(dl)
        g = Pr[Pr["arm"] == "E38-LGBM"].copy()
        rows = []
        for t_s, gg in g.groupby("t"):
            t = qk(t_s)
            tr, te = dl.train(t, K2), dl.test(t, K2)
            lr = L6.lr_predict(tr, te, E.FEATURE_SETS["COMPACT"] + ["y_last"])
            clim = float(tr["y"].mean())
            pe = {p: (te.set_index("province_code").loc[p, "y_last"]) for p in PROVS}
            for r in gg.itertuples():
                pv = pe[r.province_code]
                pp = clim if pv != pv else float(pv)
                rows.append({"target": r.target_quarter, "t": r.t, "province_code": r.province_code, "y": int(r.y),
                             "LGBM_p": r.p, "LGBM_yhat": int(r.p >= r.threshold), "LR_p": lr[r.province_code],
                             "LR_yhat": int(lr[r.province_code] >= 0.5), "PERSIST_p": pp, "PERSIST_yhat": int(pp >= 0.5),
                             "HIGH_p": 1.0, "HIGH_yhat": 1, "LOW_p": 0.0, "LOW_yhat": 0})
        R = pd.DataFrame(rows)
        arms = ["LGBM", "LR", "PERSIST", "HIGH", "LOW"]
        entry = {"eval_quarters": int(R["target"].nunique()), "rows": int(len(R)), "HIGH": int(R["y"].sum()),
                 "quarters": sorted(R["target"].unique().tolist()), "metrics": block(R, arms)}
        entry["accepted"] = {a: accepted(entry["metrics"][a], entry["metrics"]) for a in ("LGBM", "LR")}
        if name in ("T43", "PS"):
            e = P7[P7["I7_p"].notna()][["target", "province_code", "I7_p", "I7_yhat", "I7_p_price"]]
            R2 = R.merge(e, on=["target", "province_code"])
            if name == "T43":
                R2["E46_p"], R2["E46_yhat"] = R2["I7_p"], R2["I7_yhat"].astype(int)
            else:
                R2["E46_p"], R2["E46_yhat"] = R2["I7_p_price"], (R2["I7_p_price"] >= 0.5).astype(int)
            entry["with_E46"] = {"eval_quarters": int(R2["target"].nunique()), "rows": int(len(R2)), "HIGH": int(R2["y"].sum()),
                                 "metrics": block(R2, arms + ["E46"])}
            entry["with_E46"]["accepted"] = {a: accepted(entry["with_E46"]["metrics"][a], entry["with_E46"]["metrics"])
                                             for a in ("LGBM", "LR", "E46")}
            R2.to_csv(out / f"rows_{name}_withE46.csv", index=False)
        R.to_csv(out / f"rows_{name}.csv", index=False)
        res["targets"][name] = entry
    # ---------------- defensibility criteria (no model score involved)
    crit = {}
    for name in TARGETS:
        pv = prev[name]
        rshare = pv["share_HIGH_2024_2026"]
        c = {"C1_relevance": name in ("EQ3-G", "EQ3-T", "RQ", "YW", "T43", "PS"),
             "C2_within_quarter_ge_0.25": (pv["within_quarter_variance_share"] or 0) >= 0.25,
             "C3_recent_balance": rshare is not None and 0.25 <= rshare <= 0.75,
             "C4_as_of": AS_OF[name], "C5_eval_quarters_ge_8": res["targets"][name]["eval_quarters"] >= 8}
        c["all"] = all(c.values())
        crit[name] = c
    res["criteria"] = crit
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    print(stamp, "global median S1", round(med, 3))
    for n, v in prev.items():
        print(f"  {n:6s} recent HIGH {v['share_HIGH_2024_2026']} within-share {None if v['within_quarter_variance_share'] is None else round(v['within_quarter_variance_share'], 3)} by year {[(k, x['HIGH'], x['rows']) for k, x in v['by_year'].items()]}")
    for k, m in res["reproduce"].items():
        print(f"  reproduce {k}: acc {m['accuracy']:.3f} auc {m['auc']} brier {m['brier']:.3f} {m['confusion']}")
    for n, e in res["targets"].items():
        print(n, "quarters", e["eval_quarters"], "rows", e["rows"], "HIGH", e["HIGH"], "criteria", crit[n])
        for blk, ms in (("all", e["metrics"]),) + ((("withE46", e["with_E46"]["metrics"]),) if "with_E46" in e else ()):
            for a, m in ms.items():
                f = lambda v: None if v is None else round(v, 3)  # noqa: E731
                print(f"   [{blk}] {a:7s} acc {m['accuracy']:.3f} bal {f(m['balanced_accuracy'])} recH {f(m['recall_HIGH'])} "
                      f"recL {f(m['recall_LOW'])} brier {m['brier']:.3f} auc {f(m['auc'])} {m['confusion']}")
        print("   accepted:", e["accepted"], e.get("with_E46", {}).get("accepted"))


if __name__ == "__main__":
    main()
