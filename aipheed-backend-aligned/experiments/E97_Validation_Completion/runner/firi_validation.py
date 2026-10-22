"""E97 Q1-Q4 (PROTOCOL.md): the served FIRI v2 against the measured regional outcome R (SWS hunger > 11.3%), Lead 2.
Run from backend/:  py -3.13 ../aipheed-backend-aligned/experiments/E97_Validation_Completion/runner/firi_validation.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import common as C
from app.ml.inference import thesis_system as TS

LEAD, LINE = 2, 11.3
DOMS = ["A", "V", "C", "E", "N", "H"]


def outcome(all_rounds: bool = False) -> dict[str, float]:
    """R: mean of the definition_A rounds of the quarter (served rule). all_rounds=True: the FIRI v1/v2 evaluation's
    series (every round, supplementary ones included), used only to reproduce the stored numbers (Q1a)."""
    s = pd.read_csv("data/inputs/sws_rounds.csv")
    if not all_rounds:
        s = s[s["definition_A"].astype(str) == "True"]
    return s.groupby("quarter")["H"].mean().to_dict()


def posted_quarters(issue: str) -> set[str]:
    s = pd.read_csv("data/inputs/sws_rounds.csv")
    s = s[(s["definition_A"].astype(str) == "True") & (s["published"].str[:10] < issue)]
    return set(s["quarter"])


def index_from(row, drop=(), only=None) -> float | None:
    w = json.loads(row["weights_json"]) or {}
    dom = {d: row[f"dom_{d}"] for d in DOMS if pd.notna(row[f"dom_{d}"])}
    if only is not None:
        dom = {d: v for d, v in dom.items() if d == only}
    dom = {d: v for d, v in dom.items() if d not in drop}
    if not dom:
        return None
    ww = {d: float(w.get(d, 1.0)) for d in dom}
    return sum(ww[d] * dom[d] for d in dom) / sum(ww.values())


def regional(h: pd.DataFrame, fn) -> pd.Series:
    """Regional score per target = mean over provinces with a computable value (served FIRI needs >= 4 domains)."""
    ok = h["FIRI"].notna()
    v = h[ok].assign(s=[fn(r) for _, r in h[ok].iterrows()])
    return v.groupby("target")["s"].mean()


def q1(h: pd.DataFrame, R: pd.DataFrame, Rv1: pd.DataFrame, served_eval: dict) -> dict:
    res = {}
    m = C.metrics(Rv1["y"], Rv1["firi"])
    ref = served_eval["regional"]["2"]["candidates"]["C3"]
    res["Q1a"] = {"reproduced": m["confusion"] == ref["confusion"] and abs(m["accuracy"] - ref["accuracy"]) < 1e-9
                  and abs(m["brier"] - ref["brier"]) < 1e-9, "recomputed": m, "stored": {k: ref[k] for k in ("accuracy", "brier", "confusion", "n")},
                  "outcome_series": "all SWS rounds (as the stored evaluation)", "quarters": Rv1["target"].tolist(),
                  "protocol_R": {"n": len(R), "accuracy": C.metrics(R["y"], R["firi"])["accuracy"]}}
    # Q1b: H domain equals the served regional hunger probability at the origin (rounds posted before the issue)
    mism = []
    for _, r in h.iterrows():
        rh = TS.regional_hunger(TS.qi(r["origin_quarter"]), LEAD)
        p = rh.get("probabilityAbove11_3")
        if pd.isna(r["dom_H"]) != (p is None) or (p is not None and abs(float(r["dom_H"]) - p) > 6e-4):
            mism.append({"target": r["target"], "province": r["province_code"], "dom_H": r["dom_H"], "served": p})
    res["Q1b"] = {"rows": len(h), "mismatches": len(mism), "examples": mism[:5]}
    # Q1d: timeline
    bad = [r["target"] for _, r in h.iterrows()
           if TS.qi(r["target"]) - TS.qi(r["origin_quarter"]) != LEAD or r["issue_date"] != TS.issue_of(TS.qi(r["origin_quarter"]))]
    res["Q1d"] = {"rows": len(h), "violations": sorted(set(bad))}
    # Q1c: walk-forward evidence weights (FIRI2 protocol C3, as coded in the recovered firi2_evaluate.py)
    reg = h.groupby("origin_quarter")[[f"dom_{d}" for d in DOMS]].mean()
    checks, worst, wrong = 0, 0.0, []
    for _, r in h.iterrows():
        t = TS.qi(r["origin_quarter"])
        known = {TS.qs(q): v for q, v in TS._posted(r["issue_date"]).items()}
        pairs = [(reg.loc[oq], TS.qs(TS.qi(oq) + LEAD)) for oq in reg.index if TS.qi(oq) < t]
        pairs = [(dm, known[tq]) for dm, tq in pairs if tq in known]
        n, w3 = len(pairs), None
        if n >= 6:
            raw = {}
            for d in DOMS:
                xs = [(dm[f"dom_{d}"], hv) for dm, hv in pairs if pd.notna(dm[f"dom_{d}"])]
                if len(xs) < 6:
                    continue
                rho = spearmanr([a for a, _ in xs], [b for _, b in xs]).statistic
                raw[d] = max(0.0, float(rho)) if rho == rho else 0.0
            if raw and sum(raw.values()) > 0:
                tot, eq = sum(raw.values()), 1.0 / len(raw)
                w3 = {d: n / (n + 8) * raw[d] / tot + 8 / (n + 8) * eq for d in raw}
                mu = np.mean(list(w3.values()))
                w3 = {d: v / mu for d, v in w3.items()}
        stored = json.loads(r["weights_json"]) or {}
        avail = list(stored)
        w = {d: (w3 or {}).get(d, 1.0) if w3 else 1.0 for d in avail}
        wn = {d: w[d] / sum(w.values()) for d in avail}
        diff = max((abs(wn[d] - stored[d]) for d in avail), default=0.0)
        checks += 1
        worst = max(worst, diff)
        if diff > 1e-6:
            wrong.append({"target": r["target"], "province": r["province_code"], "pairs": n, "stored": stored, "recomputed": wn})
    res["Q1c"] = {"rows_checked": checks, "max_abs_weight_diff": worst, "mismatched_targets": len(wrong), "examples": wrong[:3]}
    return res


def q2(R: pd.DataFrame) -> dict:
    """Walk-forward Platt calibration of the regional FIRI; compared with H1 and climatology on the same quarters."""
    from sklearn.linear_model import LogisticRegression
    cal, clim = [], []
    for _, r in R.iterrows():
        posted = posted_quarters(r["issue"])
        past = R[R["target"].isin(posted) & (R["qi"] < r["qi"])]
        c0 = float(past["y"].mean()) if len(past) else 0.5
        clim.append(c0)
        if len(past) >= 6 and past["y"].nunique() == 2:
            m = LogisticRegression(C=1.0).fit(past[["firi"]].to_numpy(), past["y"].to_numpy())
            cal.append(float(m.predict_proba([[r["firi"]]])[0, 1]))
        else:
            cal.append(c0)
    R = R.assign(firi_cal=cal, clim=clim)
    g = R["target"].to_numpy()
    out = {"metrics": {a: C.metrics(R["y"], R[a]) for a in ("firi", "firi_cal", "h1", "clim")},
           "calibrated_quarters": int(sum(1 for _, r in R.iterrows() if r["firi_cal"] != r["clim"]))}
    out["paired_brier"] = {}
    for b in ("h1", "clim"):
        d = (R["firi_cal"] - R["y"]) ** 2 - (R[b] - R["y"]) ** 2
        out["paired_brier"][f"firi_cal_minus_{b}"] = {
            "mean": float(d.mean()), "ci95": C.boot_ci(g, lambda i: float(d.to_numpy()[i].mean())),
            "firi_cal_better_quarters": int((d < -1e-12).sum()), "worse": int((d > 1e-12).sum()), "sign_p": C.sign_test(d)}
    y = R["y"].to_numpy()

    def dstat(fn):
        return lambda i: (None if fn(y[i], R["firi"].to_numpy()[i]) is None or fn(y[i], R["h1"].to_numpy()[i]) is None
                          else fn(y[i], R["firi"].to_numpy()[i]) - fn(y[i], R["h1"].to_numpy()[i]))

    bal = lambda yy, s: C.metrics(yy, s)["balanced_accuracy"]  # noqa: E731
    out["paired_auc_firi_minus_h1"] = {"point": C.auc(y, R["firi"]) - C.auc(y, R["h1"]), "ci95": C.boot_ci(g, dstat(C.auc))}
    out["paired_balacc_firi_minus_h1"] = {"point": bal(y, R["firi"]) - bal(y, R["h1"]), "ci95": C.boot_ci(g, dstat(bal))}
    acc_d = ((R["firi"] >= 0.5).astype(int) == R["y"]).astype(int) - ((R["h1"] >= 0.5).astype(int) == R["y"]).astype(int)
    out["paired_accuracy_firi_minus_h1"] = {"point": float(acc_d.mean()), "ci95": C.boot_ci(g, lambda i: float(acc_d.to_numpy()[i].mean())),
                                            "firi_only_correct": int((acc_d > 0).sum()), "h1_only_correct": int((acc_d < 0).sum()),
                                            "sign_p": C.sign_test(acc_d)}
    decision = (out["paired_brier"]["firi_cal_minus_h1"]["ci95"][1] is not None
                and out["paired_brier"]["firi_cal_minus_h1"]["ci95"][1] < 0
                and out["paired_brier"]["firi_cal_minus_h1"]["sign_p"] < 0.05)
    out["serve_calibrated_probability"] = bool(decision)
    out["per_quarter"] = R[["target", "issue", "H", "y", "firi", "firi_cal", "h1", "clim", "last_posted"]].round(4).to_dict(orient="records")
    return out


def q3(h: pd.DataFrame, R: pd.DataFrame) -> dict:
    res = {}
    for lab, kw in [("served", {})] + [(f"drop_{d}", {"drop": (d,)}) for d in DOMS] + [(f"only_{d}", {"only": d}) for d in DOMS]:
        s = regional(h, lambda r, kw=kw: index_from(r, **kw))
        D = R[["target", "y"]].assign(s=R["target"].map(s)).dropna()
        res[lab] = {**C.metrics(D["y"], D["s"]), "quarters": len(D)}
    return res


def q4(R: pd.DataFrame) -> dict:
    on = R[(R["y"] == 1) & (R["last_posted"] <= LINE)]
    rec = R[(R["y"] == 0) & (R["last_posted"] > LINE)]
    res = {"onsets": {"quarters": on["target"].tolist(), "firi_hits": int((on["firi"] >= 0.5).sum()),
                      "h1_hits": int((on["h1"] >= 0.5).sum())},
           "recoveries": {"quarters": rec["target"].tolist(), "firi_correct": int((rec["firi"] < 0.5).sum()),
                          "h1_correct": int((rec["h1"] < 0.5).sum())}, "windows": {}}
    for lab, lo, hi in (("2022-Q2..2024-Q1", "2022-Q2", "2024-Q1"), ("2024-Q2..2026-Q3", "2024-Q2", "2026-Q3")):
        W = R[(R["target"] >= lo) & (R["target"] <= hi)]
        res["windows"][lab] = {a: C.metrics(W["y"], W[a]) for a in ("firi", "h1")}
    return res


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = C.E97 / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    h = pd.read_csv("data/thesis/firi2_history.csv", dtype={"province_code": str})
    h = h[h["kind"] == "backtest"].copy()
    reg = h.groupby("target")["FIRI"].mean()
    R, Rv1 = table(h, reg, outcome()), table(h, reg, outcome(True))
    served_eval = json.loads((TS.FIRI_EVALUATION).read_text(encoding="utf-8"))
    res = {"stamp": stamp, "protocol_sha256": (C.E97 / "PROTOCOL.sha256").read_text().split()[0],
           "evidence_status": "development evidence: every scored quarter (2022-Q2..2026-Q3) was examined before E97",
           "quarters": len(R), "Q1": q1(h, R, Rv1, served_eval), "Q2": q2(R), "Q3": q3(h, R), "Q4": q4(R),
           "Q2_v1_outcome": q2(Rv1)}
    R.to_csv(o / "firi_regional_lead2.csv", index=False)
    Rv1.to_csv(o / "firi_regional_lead2_allrounds.csv", index=False)
    report(o, res)


def table(h, reg, out):
    rows = []
    for tq, issue in h.drop_duplicates("target")[["target", "issue_date"]].itertuples(index=False):
        if tq not in out or pd.isna(reg.get(tq)):
            continue
        t = TS.qi(tq) - LEAD
        rh = TS.regional_hunger(t, LEAD)
        rows.append({"target": tq, "qi": TS.qi(tq), "issue": issue, "H": out[tq], "y": int(out[tq] > LINE),
                     "firi": float(reg[tq]), "h1": rh["probabilityAbove11_3"], "last_posted": rh["latestReading"]})
    return pd.DataFrame(rows).sort_values("qi").reset_index(drop=True)


def report(o, res):
    (o / "firi_validation.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("quarters",)}), "->", o)
    print("Q1:", json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("recomputed", "examples", "stored")} for k, v in res["Q1"].items()}, default=float))
    for a, m in res["Q2"]["metrics"].items():
        print(f"  {a:9s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy']} auc={m['auc_roc']} brier={m['brier']:.3f} {m['confusion']}")
    print("  paired:", json.dumps({k: res["Q2"][k] for k in res["Q2"] if k.startswith("paired")}, default=float))
    for a, m in res["Q3"].items():
        print(f"  Q3 {a:8s} q={m['quarters']} acc={m['accuracy']:.3f} bal={m['balanced_accuracy']} auc={m['auc_roc']}")
    print("Q4:", json.dumps({k: v for k, v in res["Q4"].items() if k != "windows"}))
    for w, v in res["Q4"]["windows"].items():
        print("  ", w, {a: (round(m["accuracy"], 3), m["confusion"]) for a, m in v.items()})


if __name__ == "__main__":
    main()
