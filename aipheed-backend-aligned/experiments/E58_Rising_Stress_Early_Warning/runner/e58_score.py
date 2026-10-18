"""E58 step 4 (PROTOCOL sections 4-5): score the SEALED warning rules against HIGH, ONSET and RISEP.

    backend/venv/Scripts/python.exe -B runner/e58_score.py  -> runs/<UTC stamp>/{rows.csv, results.json}, tables/*.csv
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E58 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E58.parent / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

F, L, np, pd = G.F, G.L, G.np, G.pd
SEALED = E58 / "sealed" / "predictions.csv"
RULES = ["C0_E56", "EW", "C1_cost", "C2_tau", "C3_cw", "C4_twostage", "B_PERSIST", "B_CLIM", "B_HIGH", "B_RECENT", "B_PROJ"]
SIMPLE = ["B_PERSIST", "B_CLIM", "B_RECENT", "B_PROJ"]


def verify():
    want = (E58 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    if hashlib.sha256((E58 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    if hashlib.sha256(SEALED.read_bytes()).hexdigest() != (SEALED.parent / "predictions.csv.sha256").read_text().split()[0]:
        raise SystemExit("sealed predictions changed")


def rates(y, w, p=None):
    y, w = np.asarray(y, int), np.asarray(w, int)
    tp, tn = int(((w == 1) & (y == 1)).sum()), int(((w == 0) & (y == 0)).sum())
    fp, fn = int(((w == 1) & (y == 0)).sum()), int(((w == 0) & (y == 1)).sum())
    dv = lambda a, b: a / b if b else None  # noqa: E731
    rh, rl = dv(tp, tp + fn), dv(tn, tn + fp)
    out = {"n": int(len(y)), "events": int(y.sum()), "warnings": int(w.sum()), "TP": tp, "TN": tn, "FP": fp, "FN": fn,
           "recall": rh, "precision": dv(tp, tp + fp), "fn_rate": dv(fn, tp + fn), "fp_rate": dv(fp, fp + tn),
           "accuracy": (tp + tn) / len(y), "balanced_accuracy": None if rh is None or rl is None else (rh + rl) / 2}
    if p is not None:
        from sklearn.metrics import roc_auc_score
        p = np.asarray(p, float)
        out["brier"] = float(np.mean((p - y) ** 2))
        out["auc"] = float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(p)) > 1 else None
    return out


def cluster_ci(S, col_w, col_y, fn, B=2000, seed=58):
    rng = np.random.default_rng(seed)
    qs = sorted(S["target"].unique())
    vals = []
    for _ in range(B):
        g = pd.concat([S[S["target"] == q] for q in rng.choice(qs, len(qs))])
        v = fn(g[col_y].to_numpy(), g[col_w].to_numpy())
        if v is not None:
            vals.append(v)
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))] if vals else None


def main():
    verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E58 / "runs" / stamp
    out.mkdir(parents=True)
    S = pd.read_csv(SEALED, dtype={"province_code": str})
    Ev = pd.read_csv(E58 / "data" / "events.csv", dtype={"province_code": str}).set_index(["t", "province_code"])
    for k in ("HIGH", "ONSET", "RISEP", "last_known_T43"):
        S[k] = [Ev.loc[(t, p), k] for t, p in zip(S["t"], S["province_code"])]
    assert (S["PERSIST_p"].fillna(-1) == S["last_known_T43"].fillna(-1)).all()
    # warning flags and the probability each rule is scored with
    S["C0_E56_w"], S["C0_E56_p"] = (S["E56_p"] >= 0.5).astype(int), S["E56_p"]
    S["EW_w"], S["EW_p"] = (S["E56_p_price"] >= 0.5).astype(int), S["E56_p_price"]
    S["C1_cost_w"], S["C1_cost_p"] = (S["E56_p"] >= 1 / 3).astype(int), S["E56_p"]
    S["C2_tau_w"], S["C2_tau_p"] = (S["E56_p_price"] >= S["C2_tau"]).astype(int), S["E56_p_price"]
    S["C3_cw_w"], S["C3_cw_p"] = (S["C3_p"] >= 0.5).astype(int), S["C3_p"]
    pr = S["C4_p_rise"].fillna(0.0)
    S["C4_twostage_w"] = ((S["E56_p"] >= 0.5) | (pr >= 0.5)).astype(int)
    S["C4_twostage_p"] = np.maximum(S["E56_p"], pr)
    S["B_PERSIST_w"], S["B_PERSIST_p"] = S["PERSIST_p"].fillna(0).astype(int), S["PERSIST_p"].fillna(0)
    S["B_CLIM_w"], S["B_CLIM_p"] = (S["CLIM_p"] >= 0.5).astype(int), S["CLIM_p"]
    S["B_HIGH_w"], S["B_HIGH_p"] = 1, 1.0
    S["B_RECENT_w"] = S["BRECENT_flag"].fillna(0).astype(int)
    S["B_RECENT_p"] = S["B_RECENT_w"].astype(float)
    S["B_PROJ_w"], S["B_PROJ_p"] = (S["BPROJ_p"] >= 0.5).astype(int), S["BPROJ_p"]
    S["new_LOW"] = (S["last_known_T43"] == 0).astype(int)
    S.to_csv(out / "rows.csv", index=False, float_format="%.12g")

    res = {"run_utc": stamp, "rows": int(len(S)), "events": {k: int(S[k].sum()) for k in ("HIGH", "ONSET", "RISEP")}, "rules": {}}
    for r in RULES:
        w, p = S[f"{r}_w"], S[f"{r}_p"]
        high = rates(S["HIGH"], w, p)
        on = S[S["new_LOW"] == 1]                              # rows where the latest known label was LOW
        onset = rates(on["ONSET"], on[f"{r}_w"])               # recall = onsets warned; precision = new-warning precision
        rise = rates(S["RISEP"], w, S["C4_p_rise"] if r == "C4_twostage" else None)
        missed = S[(S["ONSET"] == 1) & (w == 0)][["target", "province"]].to_dict("records")
        res["rules"][r] = {"HIGH": high, "ONSET": onset | {"missed": missed}, "RISEP": rise,
                           "HIGH_recall_ci": cluster_ci(S, f"{r}_w", "HIGH", lambda y, x: (x[y == 1].mean() if (y == 1).any() else None)),
                           "ONSET_recall_ci": cluster_ci(S, f"{r}_w", "ONSET", lambda y, x: (x[y == 1].mean() if (y == 1).any() else None)),
                           "accuracy_ci": cluster_ci(S, f"{r}_w", "HIGH", lambda y, x: float((x == y).mean()))}
    R = res["rules"]
    ew, c0 = R["EW"], R["C0_E56"]
    crit = {"W1_onset_recall": (ew["ONSET"]["recall"] or 0) >= 0.60 and (ew["ONSET"]["recall"] or 0) >= (c0["ONSET"]["recall"] or 0) + 0.20,
            "W2_high_recall": (ew["HIGH"]["recall"] or 0) >= 0.70,
            "W3_balanced_ge_E56": (ew["HIGH"]["balanced_accuracy"] or 0) >= (c0["HIGH"]["balanced_accuracy"] or 0),
            "W4_accuracy_ge_0.75": ew["HIGH"]["accuracy"] >= 0.75,
            "W5_fp_rate_le_0.30": (ew["HIGH"]["fp_rate"] or 0) <= 0.30,
            "W6_beats_simple_baselines": all((ew["ONSET"]["recall"] or 0) >= (R[b]["ONSET"]["recall"] or 0) and
                                             (ew["HIGH"]["balanced_accuracy"] or 0) >= (R[b]["HIGH"]["balanced_accuracy"] or 0)
                                             for b in SIMPLE)}
    crit["EW_adopted"] = all(crit.values())
    res["acceptance_EW"] = crit
    # per quarter and per province (EW and E56)
    qrows, prow = [], []
    for q, g in S.groupby("target"):
        for r in ("EW", "C0_E56"):
            h, o = rates(g["HIGH"], g[f"{r}_w"], g[f"{r}_p"]), rates(g[g["new_LOW"] == 1]["ONSET"], g[g["new_LOW"] == 1][f"{r}_w"])
            qrows.append({"target": q, "issue_quarter": g["origin_quarter"].iloc[0], "rule": r, "n": h["n"], "HIGH": h["events"],
                          "ONSET": int(g["ONSET"].sum()), "RISEP": int(g["RISEP"].sum()), "warnings": h["warnings"],
                          "TP": h["TP"], "FP": h["FP"], "FN": h["FN"], "TN": h["TN"], "accuracy": h["accuracy"],
                          "recall_HIGH": h["recall"], "precision_HIGH": h["precision"], "onsets_warned": o["TP"],
                          "brier": h["brier"], "auc": h["auc"]})
    for pv, g in S.groupby("province"):
        for r in ("EW", "C0_E56", "B_PERSIST"):
            h = rates(g["HIGH"], g[f"{r}_w"])
            o = g[(g["ONSET"] == 1)]
            prow.append({"province": pv, "rule": r, "HIGH": h["events"], "ONSET": int(g["ONSET"].sum()), "warnings": h["warnings"],
                         "recall_HIGH": h["recall"], "precision_HIGH": h["precision"], "fp": h["FP"], "fn": h["FN"],
                         "accuracy": h["accuracy"], "onsets_warned": int(o[f"{r}_w"].sum())})
    # hunger-regime cost estimate (labels only): 2021-2023 province-quarters with PS HIGH but T43 LOW
    d = L.load()
    Y = F.t43_labels(d)
    Yo = Y[(Y["q"] <= L.qi("2023-Q4")) & Y["T43"].notna()]
    res["low_hunger_regime_cost"] = {"rows_2021_2023": int(len(Yo)), "PS_HIGH": int(Yo["PS"].sum()),
                                     "PS_HIGH_but_T43_LOW": int(((Yo["PS"] == 1) & (Yo["T43"] == 0)).sum()),
                                     "note": "a perfect price-pressure warning would have flagged these as warnings that were "
                                             "not T43 HIGH (hunger at or below 11.3%)"}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    tdir = E58 / "tables"
    pd.DataFrame(qrows).round(4).to_csv(tdir / "quarter_by_quarter.csv", index=False)
    pd.DataFrame(prow).round(4).to_csv(tdir / "province_early_warning.csv", index=False)
    pd.DataFrame([{"rule": r, **{f"HIGH_{k}": v for k, v in R[r]["HIGH"].items()},
                   **{f"ONSET_{k}": v for k, v in R[r]["ONSET"].items() if k != "missed"},
                   **{f"RISEP_{k}": v for k, v in R[r]["RISEP"].items()}} for r in RULES]).round(4) \
        .to_csv(tdir / "rules_comparison.csv", index=False)
    f = lambda v: None if v is None else round(v, 3)  # noqa: E731
    print(stamp, res["events"])
    for r in RULES:
        h, o, rp = R[r]["HIGH"], R[r]["ONSET"], R[r]["RISEP"]
        print(f"  {r:12s} HIGH acc {h['accuracy']:.3f} bal {f(h['balanced_accuracy'])} rec {f(h['recall'])} prec {f(h['precision'])} "
              f"FP {h['FP']} FN {h['FN']} fpr {f(h['fp_rate'])} brier {f(h.get('brier'))} | ONSET rec {f(o['recall'])} "
              f"({o['TP']}/{o['events']}) newwarn-prec {f(o['precision'])} | RISEP rec {f(rp['recall'])} prec {f(rp['precision'])}")
    print("  EW missed onsets", R["EW"]["ONSET"]["missed"])
    print("  acceptance", crit)
    print("  CIs EW", R["EW"]["ONSET_recall_ci"], R["EW"]["HIGH_recall_ci"], R["EW"]["accuracy_ci"], "E56", R["C0_E56"]["ONSET_recall_ci"])
    print("  low-hunger cost", res["low_hunger_regime_cost"])


if __name__ == "__main__":
    main()
