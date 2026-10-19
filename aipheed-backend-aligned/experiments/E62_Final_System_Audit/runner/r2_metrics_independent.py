"""E62 r2: independent re-scoring of every sealed rolling-origin forecast on the 50 evaluation rows (targets
2024-Q2..2026-Q3), against the labels recomputed from raw files in r1 (not the experiments' own label code).

Arms (all read from sealed, hash-checked files; nothing is refitted here):
  E56            E57 sealed E56_p (served E56-TUNED procedure, P(HIGH) = P_hunger x P_price)
  E58-EW         warning form of E56: HIGH call when E56_p_price >= 0.5 (E58 rule); probability column = P_price
  E60-A          E60 gov-only candidate (E56 procedure without the old news columns)
  E60-C          E60 gov + improved news (classifier v2 features)
  E60-B          E60 improved news only (+ hunger part)
  E60-D          E60 + label history
  E61-C4         E61 no-news price part (same idea as E60-A, separate implementation)
  PERSIST, MAJORITY(as-of), CLIM(as-of), PROVCLIM(as-of), BPROJ (structural CPI projection only)

    backend/venv/Scripts/python.exe -B runner/r2_metrics_independent.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
E62 = Path(__file__).resolve().parents[1]
EXP = E62.parent
S57 = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"
S58 = EXP / "E58_Rising_Stress_Early_Warning" / "sealed" / "predictions.csv"
S60 = EXP / "E60_E58_Accuracy_Optimization" / "sealed" / "candidates.csv"
S61 = EXP / "E61_E58_Low_Forecast_Investigation" / "sealed" / "candidates.csv"
EVENTS = EXP / "E58_Rising_Stress_Early_Warning" / "data" / "events.csv"
LAB = E62 / "tables" / "r1_labels_independent.csv"
RNG = np.random.default_rng(62)


def sha_ok(p: Path) -> str:
    want = (p.parent / (p.name + ".sha256")).read_text().split()[0]
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != want:
        raise SystemExit(f"{p} does not match its seal")
    return got


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def rows() -> pd.DataFrame:
    hashes = {p.name + "@" + p.parent.parent.name: sha_ok(p) for p in (S57, S58, S60, S61)}
    a = pd.read_csv(S57, dtype={"province_code": str})
    b = pd.read_csv(S58, dtype={"province_code": str})[["t", "province_code", "BPROJ_p"]]
    c = pd.read_csv(S60, dtype={"province_code": str})
    d = pd.read_csv(S61, dtype={"province_code": str})[["t", "province_code", "C4_p", "C4_p_price"]]
    ev = pd.read_csv(EVENTS, dtype={"province_code": str})[["t", "province_code", "ONSET", "RISEP", "last_known_T43"]]
    lab = pd.read_csv(LAB, dtype={"province_code": str}).rename(columns={"quarter": "target"})
    R = a.merge(b, on=["t", "province_code"]).merge(c.drop(columns=["origin_quarter", "target"]), on=["t", "province_code"])
    R = R.merge(d, on=["t", "province_code"]).merge(ev, on=["t", "province_code"])
    R = R.merge(lab[["target", "province_code", "T43", "PS", "F", "HL", "G", "H_all", "food_margin", "gap_margin"]],
                on=["target", "province_code"], how="left")
    assert len(R) == 50 and R["T43"].notna().all(), "the 50 evaluation rows must all have an outcome"
    assert (R["T43"] == R["PS"]).all(), "on these rows hunger was always above 11.3, so T43 == PS"
    R["y"] = R["T43"].astype(int)
    R.attrs["hashes"] = hashes
    return R


ARMS = {  # name: (probability column, decision column or None -> p >= 0.5)
    "E56": ("E56_p", None), "E58-EW (warning form)": ("E56_p_price", None), "E60-A gov-only": ("A_p", None),
    "E60-A warning form": ("A_p_price", None), "E60-C gov+improved news": ("C_p", None),
    "E60-C warning form": ("C_p_price", None), "E60-B improved news only": ("B_p", None),
    "E60-B warning form": ("B_p_price", None), "E60-D +history": ("D_p", None), "E61-C4 no news": ("C4_p", None),
    "Price projection only (B-PROJ)": ("BPROJ_p", None), "Persistence": ("PERSIST_p", None),
    "Majority as-of": ("MAJORITY_p", None), "Climatology as-of": ("CLIM_p", None),
    "Province climatology as-of": ("PROVCLIM_p", None),
}


def metrics(R: pd.DataFrame, col: str) -> dict:
    y, p = R["y"].to_numpy(), np.clip(R[col].astype(float).to_numpy(), 0, 1)
    yh = (p >= 0.5).astype(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    n, pos = len(y), int(y.sum())
    pe = np.clip(p, 1e-6, 1 - 1e-6)
    out = {"n": n, "HIGH": pos, "correct": tp + tn, "accuracy": round((tp + tn) / n, 3), "accuracy_wilson95": wilson(tp + tn, n),
           "balanced_accuracy": round(0.5 * (tp / pos + tn / (n - pos)), 3),
           "HIGH_recall": round(tp / pos, 3), "HIGH_recall_wilson95": wilson(tp, pos),
           "HIGH_precision": round(tp / (tp + fp), 3) if tp + fp else None, "LOW_recall": round(tn / (n - pos), 3),
           "false_alarms": fp, "missed_HIGH": fn,
           "brier": round(float(np.mean((p - y) ** 2)), 4),
           "log_loss": round(float(-np.mean(y * np.log(pe) + (1 - y) * np.log(1 - pe))), 4),
           "calibration_in_the_large": round(float(y.mean() - p.mean()), 4)}
    on = R["ONSET"].to_numpy() == 1
    out["onsets_detected"] = f"{int(yh[on].sum())}/{int(on.sum())}"
    # quarter-cluster bootstrap for accuracy and Brier (rows in the same quarter share the hunger value)
    qs = R["target"].to_numpy()
    uq = np.unique(qs)
    acc_b, bri_b = [], []
    for _ in range(4000):
        idx = np.concatenate([np.where(qs == q)[0] for q in RNG.choice(uq, len(uq))])
        acc_b.append(float((yh[idx] == y[idx]).mean()))
        bri_b.append(float(np.mean((p[idx] - y[idx]) ** 2)))
    out["accuracy_cluster95"] = [round(float(np.quantile(acc_b, .025)), 3), round(float(np.quantile(acc_b, .975)), 3)]
    out["brier_cluster95"] = [round(float(np.quantile(bri_b, .025)), 4), round(float(np.quantile(bri_b, .975)), 4)]
    out["quarters_acc_ge_075"] = int(sum(((yh[qs == q] == y[qs == q]).mean() >= 0.75) for q in uq))
    return out


def reliability(R, col, edges=(0, .1, .2, .3, .5, .7, 1.0001)):
    y, p = R["y"].to_numpy(), R[col].astype(float).to_numpy()
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = (p >= lo) & (p < hi)
        k, n = int(y[s].sum()), int(s.sum())
        out.append({"arm_column": col, "bin": f"[{lo:.1f},{min(hi, 1.0):.1f})", "n": n,
                    "mean_p": round(float(p[s].mean()), 3) if n else None, "observed_HIGH": k,
                    "observed_rate": round(k / n, 3) if n else None, "wilson95": wilson(k, n)})
    return out


def paired(R, a, b, B=4000):
    """Paired Brier difference b - a with a quarter-cluster bootstrap CI and the quarter sign test."""
    from scipy.stats import binomtest
    y = R["y"].to_numpy()
    da = (R[a].to_numpy() - y) ** 2
    db = (R[b].to_numpy() - y) ** 2
    qs = R["target"].to_numpy()
    uq = np.unique(qs)
    per_q = np.array([db[qs == q].mean() - da[qs == q].mean() for q in uq])
    bs = []
    for _ in range(B):
        idx = np.concatenate([np.where(qs == q)[0] for q in RNG.choice(uq, len(uq))])
        bs.append(float(db[idx].mean() - da[idx].mean()))
    better, worse = int((per_q < -1e-12).sum()), int((per_q > 1e-12).sum())
    p_sign = float(binomtest(better, better + worse).pvalue) if better + worse else 1.0
    return {"reference": a, "candidate": b, "delta_brier": round(float(db.mean() - da.mean()), 4),
            "cluster95": [round(float(np.quantile(bs, .025)), 4), round(float(np.quantile(bs, .975)), 4)],
            "quarters_better": better, "quarters_worse": worse, "sign_test_p": round(p_sign, 3)}


def main():
    R = rows()
    res = {"sealed_file_sha256": R.attrs["hashes"], "arms": {}}
    for name, (col, _) in ARMS.items():
        res["arms"][name] = {"column": col, **metrics(R, col)}
    tab = pd.DataFrame([{"arm": k, **{kk: (json.dumps(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()}}
                        for k, v in res["arms"].items()])
    tab.to_csv(E62 / "tables" / "r2_model_comparison_50rows.csv", index=False, lineterminator="\n")
    res["paired_vs_E56"] = [paired(R, "E56_p", c) for c in ("A_p", "C_p", "C4_p", "BPROJ_p")]
    res["paired_news"] = [paired(R, "A_p", "C_p"), paired(R, "A_p_price", "C_p_price")]
    rel = []
    for col in ("E56_p", "E56_p_price", "A_p", "C_p"):
        rel += reliability(R, col)
    pd.DataFrame(rel).assign(wilson95=lambda f: f["wilson95"].map(json.dumps)).to_csv(
        E62 / "tables" / "r2_reliability_bins.csv", index=False, lineterminator="\n")
    # how often did low forecasts turn out HIGH?
    low = []
    for col, thr in (("E56_p", 0.2), ("E56_p_price", 0.2), ("E56_p", 0.1), ("E56_p_price", 0.1)):
        s = R[R[col] < thr]
        low.append({"column": col, "threshold": thr, "n_below": int(len(s)), "turned_HIGH": int(s["y"].sum()),
                    "rate": round(float(s["y"].mean()), 3) if len(s) else None, "wilson95": wilson(int(s["y"].sum()), len(s)),
                    "cases_HIGH": s[s["y"] == 1][["target", "province", col, "E56_p_hunger", "F", "G", "food_margin",
                                                    "gap_margin"]].round(3).to_dict("records")})
    res["low_probability_followed_by_HIGH"] = low
    # per quarter / per province for the served E56 and its warning form
    R["E56_call"] = (R["E56_p"] >= 0.5).astype(int)
    R["EW_call"] = (R["E56_p_price"] >= 0.5).astype(int)
    pq = R.groupby("target").apply(lambda g: pd.Series({
        "n": len(g), "HIGH": int(g["y"].sum()), "E56_correct": int((g["E56_call"] == g["y"]).sum()),
        "EW_correct": int((g["EW_call"] == g["y"]).sum()), "mean_E56_p": round(g["E56_p"].mean(), 3),
        "mean_P_price": round(g["E56_p_price"].mean(), 3), "P_hunger": round(g["E56_p_hunger"].iloc[0], 3),
        "H_observed": round(g["H_all"].iloc[0], 2), "H_last_known_at_issue": g["H_last_known"].iloc[0],
        "brier_E56": round(float(((g["E56_p"] - g["y"]) ** 2).mean()), 4)}), include_groups=False).reset_index()
    pq.to_csv(E62 / "tables" / "r2_by_quarter.csv", index=False, lineterminator="\n")
    pp = R.groupby("province").apply(lambda g: pd.Series({
        "n": len(g), "HIGH": int(g["y"].sum()), "E56_correct": int((g["E56_call"] == g["y"]).sum()),
        "EW_correct": int((g["EW_call"] == g["y"]).sum()), "brier_E56": round(float(((g["E56_p"] - g["y"]) ** 2).mean()), 4),
        "brier_P_price": round(float(((g["E56_p_price"] - g["y"]) ** 2).mean()), 4)}), include_groups=False).reset_index()
    pp.to_csv(E62 / "tables" / "r2_by_province.csv", index=False, lineterminator="\n")
    R.to_csv(E62 / "tables" / "r2_rows50.csv", index=False, float_format="%.6g", lineterminator="\n")
    (E62 / "out" / "r2_metrics.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    show = ["correct", "accuracy", "accuracy_cluster95", "balanced_accuracy", "HIGH_recall", "HIGH_precision",
            "LOW_recall", "brier", "brier_cluster95", "log_loss", "onsets_detected", "quarters_acc_ge_075"]
    print(tab.set_index("arm")[show].to_string())
    print(json.dumps(res["paired_vs_E56"] + res["paired_news"], indent=0))
    print(json.dumps([{k: v for k, v in x.items() if k != "cases_HIGH"} for x in low], indent=0))
    print(pq.to_string())
    print(pp.to_string())


if __name__ == "__main__":
    main()
