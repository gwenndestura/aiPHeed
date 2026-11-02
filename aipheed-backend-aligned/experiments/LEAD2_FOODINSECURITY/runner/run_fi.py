"""LEAD2_FOODINSECURITY (PLAN.md, EXPLORATORY): Lead-1 / Lead-2 reliability under a hunger-only target
(Balance Luzon hunger > 11.3). Models PERSIST, PIH (served pi_H4) and LOGIT (12 families + h_last); baselines
ALWAYS-HIGH, ALWAYS-LOW, persistence and CLIM; the frozen R1-R7 code of P0H4_LEAD12_REVIEW/runner/reproduce.py.

Read-only inputs; writes out/ only.

    python -B run_fi.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOTD = HERE.parent
EXP = ROOTD.parent
ROOT = EXP.parents[1]
OUT = ROOTD / "out"

_spec = importlib.util.spec_from_file_location("p0h4_reproduce", EXP / "P0H4_LEAD12_REVIEW" / "runner" / "reproduce.py")
RP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RP)
sys.path.insert(0, str(EXP / "FINAL_UNIFIED_LGBM" / "runner"))
import uni_lib as U  # noqa: E402

np, pd = RP.np, RP.pd
C, E, L, FM = U.C, U.E, U.L, U.C.FM
LEADS = (1, 2)
EXPECT = {1: (14, 70), 2: (13, 65)}                                  # PLAN section 3
MODELS = ("PERSIST", "PIH", "LOGIT")
BASELINES = ("ALWAYS-HIGH", "ALWAYS-LOW", "CLIM")
FIRST_Q = L.qi("2021-Q1")


def plan_ok() -> str:
    b = (ROOTD / "PLAN.md").read_bytes()
    i = b.rfind(b"\nPLAN-SHA256:") + 1
    h = hashlib.sha256(b[:i]).hexdigest()
    if h != b[i:].split(b":", 1)[1].strip().decode():
        raise SystemExit("PLAN.md changed after it was hashed")
    return h


# ================================================================================================ labels and baselines
def bl_rounds() -> pd.DataFrame:
    r = FM.rounds("primary")
    return r[r["area"] == "BL"]


def done_quarters(iss, rounds: pd.DataFrame) -> set[int]:
    """Balance Luzon quarters whose every round was published before iss."""
    return {int(q) for q, g in rounds.groupby("q") if (g["published"] < iss).all()}


def hunger_label(q: int) -> int:
    return int(C.bl_quarters()[q] > C.H_LINE)


def clim(t: int, rounds: pd.DataFrame) -> float:
    qs_ = sorted(q for q in done_quarters(E.issue(t), rounds) if q >= FIRST_Q)
    return float(np.mean([hunger_label(q) for q in qs_])) if qs_ else 0.0


# ================================================================================================ model (c) LOGIT
def logit_forecast(S: pd.DataFrame, t: int, k: int, rounds: pd.DataFrame, feats: list[str]) -> tuple[np.ndarray, str]:
    from sklearn.linear_model import LogisticRegression
    iss = E.issue(t)
    done = done_quarters(iss, rounds)
    tr = S[(S["lead"] == k) & (S["t"] < t) & (S["target_q"] <= t - 1) & S["target_q"].isin(done)].copy()
    te = S[(S["lead"] == k) & (S["t"] == t)].sort_values("province_code")
    for q in tr["target_q"].unique():                                 # PLAN section 7, first check
        g = rounds[rounds["q"] == q]
        assert len(g) and (g["published"] < iss).all() and q <= t - 1, f"training label {L.qs(q)} not known at {iss}"
    if not len(tr):
        return np.full(len(te), clim(t, rounds)), "no_training_rows"
    y = np.array([hunger_label(int(q)) for q in tr["target_q"]])
    if len(set(y)) < 2:
        return np.full(len(te), float(y.mean())), "one_class"
    Xtr, Xte = tr[feats].astype(float), te[feats].astype(float)
    med = Xtr.median()
    keep = [c for c in feats if not np.isnan(med[c])]
    Xtr, Xte = Xtr[keep].fillna(med[keep]), Xte[keep].fillna(med[keep])
    mu, sd = Xtr.mean(), Xtr.std(ddof=0)
    keep = [c for c in keep if sd[c] > 0]
    Ztr, Zte = (Xtr[keep] - mu[keep]) / sd[keep], (Xte[keep] - mu[keep]) / sd[keep]
    m = LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=5000).fit(Ztr.to_numpy(), y)
    return m.predict_proba(Zte.to_numpy())[:, 1], f"fit ({len(tr)} rows, {tr['target_q'].nunique()} quarters, {len(keep)} cols)"


# ================================================================================================ evaluation
def _scores_safe(g, col=None, thr=0.5):
    """reproduce.scores with precision undefined (no HIGH forecast) set to 0.0, as R6 itself treats it."""
    s = _orig_scores(g, RP.P if col is None else col, thr)
    if s["precision"] is None:
        s["precision"], s["precisionUndefined"] = 0.0, True
    return s


_orig_scores = RP.scores


def evaluate(g: pd.DataFrame, col: str) -> dict:
    RP.P = col
    RP.scores = _scores_safe
    try:
        s = _scores_safe(g, col)
        rules = RP.rules(g)
    finally:
        RP.scores = _orig_scores
    if g[col].nunique() == 1:
        s["auc"] = s["prAuc"] = None                                  # PLAN: undefined for a constant forecast
    s["rules"] = rules
    s["rulesPassed"] = sum(v["pass"] for v in rules.values())
    s["failed"] = [k.split()[0] for k, v in rules.items() if not v["pass"]]
    s["R1_in_quarters"] = {"pass": bool(s["quarters"] >= 40), "value": f"{s['quarters']} quarters (>= 40 needed)"}
    br = {}
    for b in ("ALWAYS-HIGH_p", "PERSIST-SI_p"):
        diff = float(np.mean((g[col] - g["y"]) ** 2 - (g[b] - g["y"]) ** 2))
        bs = RP.boot_quarters(g, lambda h, b=b: float(np.mean((h[col] - h["y"]) ** 2 - (h[b] - h["y"]) ** 2)))
        br[b[:-2]] = {"brierDiff": round(diff, 4), "lower": bool(diff < 0), "p_one_sided": float(np.mean(np.asarray(bs) >= 0))}
    s["brierVs"] = br
    s["reliable"] = bool(not s["failed"] and br["ALWAYS-HIGH"]["lower"] and br["PERSIST-SI"]["lower"])
    return s


def main():
    sha = plan_ok()
    OUT.mkdir(parents=True, exist_ok=True)
    U.setup()
    rounds = bl_rounds()
    d = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    d = d[d["lead"].isin(LEADS)][["t", "lead", "province_code", "q", "hunger", "h_last", "pi_H4"]].copy()
    assert ((d["q"] - d["t"]) == d["lead"]).all() and not d.duplicated(["lead", "province_code", "q"]).any()
    for k, (nq, nr) in EXPECT.items():
        g = d[d["lead"] == k]
        assert (g["q"].nunique(), len(g)) == (nq, nr), f"lead {k}: {g['q'].nunique()} q, {len(g)} rows"
    assert all(hunger_label(int(q)) == int(h) for q, h in zip(d["q"], d["hunger"])), "hunger label mismatch"

    served = pd.read_csv(ROOT / "backend" / "data" / "ch1_engine" / "rows.csv", dtype={"province_code": str})
    s1 = served[served["lead"] == 1].assign(q=lambda x: x["quarter"].map(L.qi))
    j = d[d["lead"] == 1].merge(s1[["province_code", "q", "pi_hunger"]], on=["province_code", "q"])
    assert len(j) == EXPECT[1][1] and float((j["pi_H4"] - j["pi_hunger"]).abs().max()) < 1e-6, "pi_H4 != served pi_hunger"

    print("building the 12-family table (uni_lib.stack(2)) ...", flush=True)
    S = U.stack(2)
    feats = list(C.COLS) + ["h_last"]
    out_rows, fallback = [], {}
    for (t, k), g in d.groupby(["t", "lead"]):
        t, k = int(t), int(k)
        iss = E.issue(t)
        kn = FM.known(iss, "BL", "primary")
        te = S[(S["lead"] == k) & (S["t"] == t)].sort_values("province_code")
        assert list(te["province_code"]) == sorted(g["province_code"]), f"{L.qs(t)} lead {k}: rows differ"
        assert (pd.to_datetime(te["sws_newest_published"]) < pd.Timestamp(iss)).all(), f"{L.qs(t)}: SWS after issue"
        assert abs(kn[-1][1] - g["h_last"].iloc[0]) < 1e-9 and np.allclose(te["h_last"], kn[-1][1]), f"{L.qs(t)}: h_last"
        p_logit, how = logit_forecast(S, t, k, rounds, feats)
        fallback.setdefault(k, {})[L.qs(t)] = how
        cl = clim(t, rounds)
        g = g.sort_values("province_code")
        out_rows.append(g.assign(target=g["q"].map(L.qs), origin=L.qs(t), y=g["hunger"].astype(int),
                                 PERSIST=(g["h_last"] > C.H_LINE).astype(float), PIH=g["pi_H4"],
                                 LOGIT=p_logit, **{"ALWAYS-HIGH": 1.0, "ALWAYS-LOW": 0.0, "CLIM": cl}))
    R = pd.concat(out_rows, ignore_index=True)
    R = R.assign(**{"ALWAYS-HIGH_p": 1.0, "ALWAYS-LOW_p": 0.0, "PERSIST-SI_p": R["PERSIST"], "CLIM_p": R["CLIM"]})
    R.drop(columns=["ALWAYS-HIGH_p", "ALWAYS-LOW_p", "PERSIST-SI_p", "CLIM_p"]).to_csv(OUT / "rows.csv", index=False)

    res = {"label": "EXPLORATORY (closed 2023-2026 quarters; candidate only)", "planSha256": sha,
           "target": "BL hunger > 11.3 (no price condition)", "decisionRule": "HIGH at p >= 0.50",
           "logitFits": fallback, "leads": {}}
    for k in LEADS:
        g = R[R["lead"] == k]
        lk = {"quarters": int(g["q"].nunique()), "rows": len(g), "highQuarters": int(g.drop_duplicates("q")["y"].sum()),
              "models": {m: evaluate(g, m) for m in MODELS + BASELINES}}
        lg = g.assign(_hi=(g["LOGIT"] >= .5).astype(int)).groupby("q")["_hi"].nunique()
        lk["logitProvinceDisagreementQuarters"] = int((lg > 1).sum())
        lk["perQuarter"] = [{"target": r.target, "origin": r.origin, "y": int(r.y), "h_last": round(r.h_last, 2),
                             "PERSIST": r.PERSIST, "PIH": round(r.PIH, 3), "CLIM": round(r.CLIM, 3),
                             "LOGIT_mean": round(float(g[g["q"] == r.q]["LOGIT"].mean()), 3),
                             "LOGIT_high_provinces": int((g[g["q"] == r.q]["LOGIT"] >= .5).sum())}
                            for r in g.drop_duplicates("q").sort_values("q").itertuples()]
        res["leads"][str(k)] = lk
        print(f"\n=== Lead {k}: {lk['quarters']} quarters ({lk['rows']} rows), {lk['highQuarters']} HIGH quarters")
        for m, s in lk["models"].items():
            bv = s["brierVs"]
            auc = "-" if s["auc"] is None else f"{s['auc']:.3f}"
            print(f"{m:12s} TP/FP/FN/TN {s['TP']}/{s['FP']}/{s['FN']}/{s['TN']}  acc {s['accuracy']:.3f}  bal {s['balanced']:.3f} "
                  f" P {s['precision']:.3f} R {s['recall']:.3f}  AUC {auc}  "
                  f"Brier {s['brier']:.4f} | pass {s['rulesPassed']}/7 fails {s['failed']} | vs ALWAYS-HIGH "
                  f"{bv['ALWAYS-HIGH']['brierDiff']:+.4f} p {bv['ALWAYS-HIGH']['p_one_sided']:.3f}, vs PERSIST "
                  f"{bv['PERSIST-SI']['brierDiff']:+.4f} p {bv['PERSIST-SI']['p_one_sided']:.3f} | RELIABLE {s['reliable']}")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
