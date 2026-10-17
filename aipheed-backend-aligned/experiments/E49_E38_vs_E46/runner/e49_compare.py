"""E49 single run under the frozen PROTOCOL.md: reproductions, Target A (thesis Eq. 3, E38's as-of tau) and Target B
(T43) comparisons of E38 and E46 on identical rows, baselines, per-quarter results, score variation.
Runs inside the E32 data guard (E38's code installs it); writes are confined to E49.

    backend/venv/Scripts/python.exe -B runner/e49_compare.py   -> runs/<UTC stamp>/{rows.csv, results.json}
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E49 = Path(__file__).resolve().parents[1]
EXP = E49.parent
sys.path.insert(0, str(EXP / "E38_Lead2_Diagnosis_Tuning" / "runner"))
import e38_lib as E  # noqa: E402  (installs the E32 guard)

E.L7.L6.guard32.EXP = E49            # writes confined to this experiment (and the OS temp directory)
np, pd, qk, qs, PROVS = E.np, E.pd, E.qk, E.qs, E.PROVS
from scipy.stats import norm  # noqa: E402

RUN38 = EXP / "E38_Lead2_Diagnosis_Tuning" / "runs" / "20261015T033922Z" / "predictions.csv"
RUN7 = EXP / "E46_Rice_Policy" / "runs" / "i7_20261017T000111Z"


def verify() -> str:
    want = (E49 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E49 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


class DataT43(E.Data):
    """E38's data with every label replaced by the T43 label (same posting rule, same features otherwise)."""

    def __init__(self, t43: dict, pers: dict):
        super().__init__()
        self.t43, self.pers = t43, pers

    def label(self, p, target, t):
        return self.t43.get((p, target))

    def features(self, t, k):
        X = super().features(t, k).copy()
        X["y_last"] = [self.pers.get((t, p), np.nan) for p in X["province_code"]]
        return X

    def training_pairs(self, t, k):
        tr = super().training_pairs(t, k)
        if tr.empty:
            return tr
        tr = tr.copy()
        tr["y"] = [self.t43.get((p, q)) for p, q in zip(tr["province_code"], tr["target_q"])]
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
            "balanced_accuracy": None if rh is None or rl is None else (rh + rl) / 2,
            "recall_HIGH": rh, "recall_LOW": rl, "precision_HIGH": pr,
            "f1_HIGH": (2 * pr * rh / (pr + rh)) if pr and rh else None, "brier": float(np.mean((p - y) ** 2)),
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(p)) > 1 else None,
            "confusion": {"TP": tp, "TN": tn, "FP": fp, "FN": fn}, "share_HIGH_calls": float(yhat.mean())}


def date_ci(df, a, n=2000, seed=49):
    rng = np.random.default_rng(seed)
    qs_ = df["target"].unique()
    vals = [float(np.mean(np.concatenate([(df[df["target"] == q][f"{a}_yhat"] == df[df["target"] == q]["y"]).to_numpy()
                                          for q in rng.choice(qs_, len(qs_))]))) for _ in range(n)]
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def block(df, arms):
    out = {}
    for a in arms:
        m = metrics(df["y"], df[f"{a}_yhat"], df[f"{a}_p"])
        m["accuracy_ci95"] = date_ci(df, a)
        m["by_quarter"] = {q: float((g[f"{a}_yhat"] == g["y"]).mean()) for q, g in df.groupby("target")}
        m["probability_variation"] = {p: {"sd": float(g[f"{a}_p"].std(ddof=0)), "range": float(g[f"{a}_p"].max() - g[f"{a}_p"].min())}
                                      for p, g in df.groupby("province_code")}
        out[a] = m
    return out


def main():
    proto = verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E49 / "runs" / stamp
    out.mkdir(parents=True)
    d = E.Data()
    lab43 = pd.read_csv(E49 / "data" / "t43_labels.csv", dtype={"province_code": str})
    t43 = {(p, int(q)): int(y) for p, q, y in zip(lab43["province_code"], lab43["q"], lab43["y"])}
    pr43 = pd.read_csv(E49 / "data" / "t43_persistence.csv", dtype={"province_code": str})
    pers = {(int(t), p): (np.nan if pd.isna(v) else float(v)) for t, p, v in zip(pr43["t"], pr43["province_code"], pr43["y_last_t43"])}
    res = {"protocol_sha256": proto, "run_utc": stamp,
           "evidence_status": "DEVELOPMENT evidence: all quarters examined in E36-E48; no unseen quarter (PROTOCOL 0)."}

    # ---------------- reproductions
    P38 = pd.read_csv(RUN38, dtype={"province_code": str})
    e38 = P38[P38["arm"] == "E38-LGBM"].copy()
    e38["yhat"] = (e38["p"] >= e38["threshold"]).astype(int)
    res["reproduce_E38"] = {"correct": int((e38["yhat"] == e38["y"]).sum()), "n": int(len(e38)),
                            **metrics(e38["y"], e38["yhat"], e38["p"])}
    P7 = pd.read_csv(RUN7 / "predictions_i7.csv", dtype={"province_code": str})
    sel7 = json.loads((RUN7 / "selections_i7.json").read_text())["I7"]
    P7["target"] = (P7["t"] + 2).map(qs)
    P7["y43"] = [t43.get((p, int(t) + 2)) for p, t in zip(P7["province_code"], P7["t"])]
    s44 = P7[P7["I7_p"].notna() & P7["y43"].notna() & (P7["t"] + 2 >= qk("2024-Q3")) & (P7["t"] + 2 <= qk("2026-Q3"))]
    res["reproduce_E46_I7"] = metrics(s44["y43"], s44["I7_yhat"], s44["I7_p"])

    # ---------------- Target A: Eq. 3 with E38's as-of tau
    rowsA = []
    errs = {}                                      # (t) -> S1_hat - S1 per province, for the as-of error scale
    for t in sorted(P7["t"].unique()):
        g = P7[(P7["t"] == t) & P7["I7_F_hat"].notna()].set_index("province_code")
        if len(g) < 5 or qs(int(t)) not in sel7:
            continue
        t = int(t)
        s = sel7[qs(t)]
        Dh = g["I7_F_hat"] - g["I7_F_hat"].mean()
        S1h = s["H_hat"] + 2 * Dh
        tau = d.tau(t)
        posted = set(d.posted_quarters(E.L7.origin(t)))
        prior = [tp for tp in errs if tp + 2 <= t - 1 and (tp + 2) in posted]
        e = np.concatenate([errs[tp] for tp in prior]) if prior else np.array([])
        sc = float(np.sqrt(np.mean(e ** 2))) if len(prior) >= 3 else float(np.sqrt(s["hunger_rmse"] ** 2 + 3.2 * s["food_rmse"] ** 2))
        truth = np.array([d.Sv.get((p, t + 2), np.nan) for p in PROVS])
        if np.isfinite(truth).all():
            errs[t] = S1h.loc[PROVS].to_numpy() - truth
        for i, p in enumerate(PROVS):
            pA = float(1 - norm.cdf((tau - S1h[p]) / sc))
            yA = d.label(p, t + 2, t)
            rowsA.append({"t": qs(t), "target": qs(t + 2), "province_code": p, "y": yA, "E46toEQ3_p": pA,
                          "E46toEQ3_yhat": int(pA >= 0.5), "tau": tau, "S1_hat": float(S1h[p]), "scale": sc,
                          "scale_from_prior_targets": len(prior)})
    A = pd.DataFrame(rowsA).dropna(subset=["y"])
    A = A.merge(e38[["target_quarter", "province_code", "p", "yhat", "y"]].rename(
        columns={"target_quarter": "target", "p": "E38_p", "yhat": "E38_yhat", "y": "y_e38"}), on=["target", "province_code"])
    res["targetA_label_check"] = bool((A["y"].astype(int) == A["y_e38"].astype(int)).all())
    b1 = P38[P38["arm"] == "B1_PERSISTENCE"][["target_quarter", "province_code", "p"]].rename(
        columns={"target_quarter": "target", "p": "PERSIST_p"})
    A = A.merge(b1, on=["target", "province_code"])
    A["PERSIST_yhat"] = (A["PERSIST_p"] >= 0.5).astype(int)

    # ---------------- Target B: T43
    dB = DataT43(t43, pers)
    PrB, infoB = E.walk_forward(dB)
    eB = PrB[PrB["arm"] == "E38-LGBM"].copy()
    eB["yhat"] = (eB["p"] >= eB["threshold"]).astype(int)
    B = P7[P7["I7_p"].notna() & P7["y43"].notna()][["target", "province_code", "I7_p", "I7_yhat", "y43", "t"]].rename(
        columns={"I7_p": "E46_p", "I7_yhat": "E46_yhat", "y43": "y"})
    B = B.merge(eB[["target_quarter", "province_code", "p", "yhat", "y"]].rename(
        columns={"target_quarter": "target", "p": "E38toT43_p", "yhat": "E38toT43_yhat", "y": "y_check"}),
        on=["target", "province_code"])
    res["targetB_label_check"] = bool((B["y"].astype(int) == B["y_check"].astype(int)).all())
    B["PERSIST_p"] = [pers.get((int(t), p), np.nan) for t, p in zip(B["t"], B["province_code"])]
    B = B.dropna(subset=["PERSIST_p"])
    B["PERSIST_yhat"] = B["PERSIST_p"].astype(int)

    # ---------------- identical rows for both targets
    keys = sorted(set(map(tuple, A[["target", "province_code"]].to_numpy())) & set(map(tuple, B[["target", "province_code"]].to_numpy())))
    common = pd.DataFrame(keys, columns=["target", "province_code"])
    A, B = A.merge(common), B.merge(common)
    for D_ in (A, B):
        D_["LOW_p"], D_["LOW_yhat"], D_["HIGH_p"], D_["HIGH_yhat"] = 0.0, 0, 1.0, 1
    res["identical_rows"] = {"rows": int(len(common)), "independent_quarters": int(common["target"].nunique()),
                             "quarters": sorted(common["target"].unique().tolist())}
    res["targetA_EQ3"] = {"HIGH": int(A["y"].sum()), "metrics": block(A, ["E38", "E46toEQ3", "PERSIST", "LOW", "HIGH"])}
    res["targetB_T43"] = {"HIGH": int(B["y"].sum()), "metrics": block(B, ["E46", "E38toT43", "PERSIST", "LOW", "HIGH"])}
    res["E38toT43_selection_path"] = infoB["path"]
    A.to_csv(out / "rows_targetA.csv", index=False)
    B.to_csv(out / "rows_targetB.csv", index=False)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    print(stamp, "identical rows", res["identical_rows"])
    print("reproduce E38", res["reproduce_E38"]["correct"], "/", res["reproduce_E38"]["n"], "| reproduce E46 I7 acc",
          round(res["reproduce_E46_I7"]["accuracy"], 3), "| label checks A/B", res["targetA_label_check"], res["targetB_label_check"])
    for tg in ("targetA_EQ3", "targetB_T43"):
        print(tg, "HIGH", res[tg]["HIGH"])
        for a, m in res[tg]["metrics"].items():
            f = lambda v: None if v is None else round(v, 3)  # noqa: E731
            print(f"  {a:9s} acc {m['accuracy']:.3f} {[round(v, 2) for v in m['accuracy_ci95']]} bal {f(m['balanced_accuracy'])} "
                  f"recH {f(m['recall_HIGH'])} recL {f(m['recall_LOW'])} prec {f(m['precision_HIGH'])} brier {m['brier']:.3f} "
                  f"auc {f(m['auc'])} {m['confusion']} HIGHcalls {m['share_HIGH_calls']:.2f}")


if __name__ == "__main__":
    main()
