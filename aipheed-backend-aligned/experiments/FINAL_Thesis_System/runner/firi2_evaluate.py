"""FIRI v2 optimization run (FIRI2_PROTOCOL.md, frozen sha in FIRI2_PROTOCOL_SHA256.txt). Scores C0-C3 and the
LightGBM checks L1/L2 on identical data, applies the selection rule once, and writes:

  out/firi2/rows.csv, out/firi2/regional.csv, out/firi2/evaluation.json, out/firi2_sealed_prospective.csv
  backend/data/thesis/firi2_reference.json   (prior values + per-origin weights of the selected candidate)
  backend/data/thesis/firi2_history.csv      (selected candidate, Lead-2 back-test + forward origins)
  backend/data/thesis/firi2_evaluation.json  (served by the thesis mode)

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/FINAL_Thesis_System/runner/firi2_evaluate.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import final_evaluation as FE  # noqa: E402

H, F, L, np, pd = FE.H, FE.F, FE.L, FE.np, FE.pd
E = FE.G.E
from scipy.stats import binomtest, spearmanr  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

BACKEND = FE.H.BACKEND
sys.path.insert(0, str(BACKEND))
from app.ml.inference import climate_watch as CW  # noqa: E402
from app.ml.inference import firi as FI  # noqa: E402
from app.ml.inference import thesis_system as TS  # noqa: E402
from app.news import pipeline_v3 as P3  # noqa: E402

EXP = FE.EXP
OUT = HERE.parent / "out" / "firi2"
SEAL = HERE.parent / "out" / "firi2_sealed_prospective.csv"
E68_SEAL = EXP / "E68_Resolve_E67_Critical_Failures" / "sealed" / "prospective.csv"
REF = BACKEND / "data" / "thesis" / "firi2_reference.json"
HIST = BACKEND / "data" / "thesis" / "firi2_history.csv"
EVAL = BACKEND / "data" / "thesis" / "firi2_evaluation.json"
DOMS = list(FI.DOMAINS)
CANDS = ["C0", "C1", "C2", "C3"]
SHRINK_K, MIN_PAIRS, MIN_ORIGINS = 8, 6, 8
LEAD_ORIGINS = {1: ("2021-Q4", "2026-Q2"), 2: ("2021-Q4", "2026-Q1"), 3: ("2021-Q4", "2025-Q4")}


def verify():
    want = (HERE / "FIRI2_PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((HERE.parent / "FIRI2_PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert got == want, "FIRI2_PROTOCOL.md changed after freezing"
    return got


# ------------------------------------------------------------------------------------------------ inputs
def base_panel(X):
    """Lead-agnostic raw indicators for every province and origin (A1 and H1 are set per lead)."""
    rows = {}
    for t in sorted(int(v) for v in X["t"].unique()):
        issue = str(L.origin(t).date())
        haz = CW.hazard(issue)[0]
        for code in FI.PROVINCES:
            r = X[(X["t"] == t) & (X["province_code"] == code)]
            if r.empty:
                continue
            rows[(t, code)] = FI.raw_indicators(code, r.iloc[0].to_dict(), None, issue, L.qs(t), haz, None,
                                                P3.fssi_v3(code, t))
    return rows


def prior_values(base, t):
    """Values of each continuous indicator at origins strictly before t (national series: one per origin)."""
    pv = {k: [] for k in FI.CONTINUOUS}
    seen = set()
    for (tt, code), raw in base.items():
        if tt >= t:
            continue
        for k in FI.CONTINUOUS:
            x = raw[k]["x"]
            if x is None:
                continue
            if k in FI.NATIONAL:
                if (k, tt) in seen:
                    continue
                seen.add((k, tt))
            pv[k].append(float(x))
    return pv


def a1_sources():
    S63 = pd.read_csv(FE.E63 / "sealed" / "predictions.csv", dtype={"province_code": str})
    out = {(int(r.lead), int(r.t), r.province_code): float(r.E56_p_price) for r in S63.itertuples()}
    hun = {(int(r.lead), int(r.t), r.province_code): float(r.E56_p_hunger) for r in S63.itertuples()}
    S68 = pd.read_csv(E68_SEAL, dtype={"province_code": str})
    for r in S68[S68["arm"] == "A0"].itertuples():
        out[(2, L.qi(r.origin_quarter), r.province_code)] = float(r.p_price)
    return out, hun, S63


def outcome_series():
    allr = pd.read_csv(L.SWS_FILE)
    return allr.groupby("quarter")["H"].mean().to_dict()          # the v1 regional outcome series


# ------------------------------------------------------------------------------------------------ scoring
def lead_rows(base, a1, lead, t_from, t_to):
    out = []
    for (t, code), raw0 in sorted(base.items()):
        if not (L.qi(t_from) <= t <= L.qi(t_to)):
            continue
        raw = {k: dict(v) for k, v in raw0.items()}
        p = a1.get((lead, t, code))
        raw["A1"] = {"x": p, "status": "observed" if p is not None else "missing", "note": ""}
        h = TS.regional_hunger(t, lead).get("probabilityAbove11_3")
        raw["H1"] = {"x": h, "status": "observed" if h is not None else "missing", "note": ""}
        out.append((t, code, raw))
    return out


def redundancy_weights(hist_dom):
    """C2: w_d proportional to 1/(1 + sum of positive Spearman correlations with the other domains); mean 1."""
    D = pd.DataFrame(hist_dom)
    if D.empty or D["t"].nunique() < MIN_ORIGINS:
        return None
    C = D[DOMS].corr(method="spearman", min_periods=8)
    w = {}
    for d in DOMS:
        if d not in C or C[d].notna().sum() <= 1:
            continue
        s = sum(max(0.0, float(C.loc[d, o])) for o in DOMS if o != d and pd.notna(C.loc[d, o]))
        w[d] = 1.0 / (1.0 + s)
    m = np.mean(list(w.values())) if w else 1.0
    return {d: v / m for d, v in w.items()}


def evidence_weights(reg_hist, outcome_known):
    """C3: walk-forward Spearman of the regional mean domain score at t' with the observed hunger level at t'+lead,
    only pairs whose outcome was posted before the issue; shrunk to equal (k = 8); mean 1."""
    pairs = [(dm, outcome_known[tq]) for dm, tq in reg_hist if tq in outcome_known]
    n = len(pairs)
    if n < MIN_PAIRS:
        return None, n
    raw = {}
    for d in DOMS:
        xs = [(dm.get(d), h) for dm, h in pairs if dm.get(d) is not None]
        if len(xs) < MIN_PAIRS:
            continue
        rho = spearmanr([a for a, _ in xs], [b for _, b in xs]).correlation
        raw[d] = max(0.0, float(rho)) if rho == rho else 0.0
    if not raw or sum(raw.values()) <= 0:
        return None, n
    tot = sum(raw.values())
    wr = {d: v / tot for d, v in raw.items()}
    eq = 1.0 / len(raw)
    w = {d: n / (n + SHRINK_K) * wr[d] + SHRINK_K / (n + SHRINK_K) * eq for d in raw}
    m = np.mean(list(w.values()))
    return {d: v / m for d, v in w.items()}, n


def score_lead(base, a1, lead):
    t_from, t_to = LEAD_ORIGINS[lead]
    # forward origins for the served history (lead 2 only): through the record origin 2026-Q3
    if lead == 2:
        t_to = "2026-Q3"
    rows = lead_rows(base, a1, lead, t_from, t_to)
    anc = FI.anchors()
    recs, c1_dom_hist, reg_hist, weights_by_t = [], [], [], {}
    for t in sorted({r[0] for r in rows}):
        issue = TS.issue_of(t)
        pv = prior_values(base, t)
        known = TS._posted(issue)
        known_q = {L.qs(q): h for q, h in known.items()}
        w2 = redundancy_weights([x for x in c1_dom_hist if x["t"] < t])
        w3, npairs = evidence_weights([(dm, tq) for (tt, dm, tq) in reg_hist if tt < t], known_q)
        weights_by_t[L.qs(t)] = {"C2": w2, "C3": w3, "C3_pairs": npairs}
        cur_dom = []
        for (tt, code, raw) in [r for r in rows if r[0] == t]:
            s0 = FI.score(raw, anc)
            s1 = FI.score_v2(raw, pv)
            s2 = FI.score_v2(raw, pv, w2)
            s3 = FI.score_v2(raw, pv, w3)
            recs.append({"lead": lead, "t": t, "origin_quarter": L.qs(t), "issue_date": issue, "target": L.qs(t + lead),
                         "province_code": code, "C0": s0["firi"], "C1": s1["firi"], "C2": s2["firi"], "C3": s3["firi"],
                         **{f"C1_dom_{d}": s1["domains"][d] for d in DOMS},
                         **{f"C1_ind_{k}": s1["indicators"][k]["score"] for k in FI.CONTINUOUS},
                         "C1_domains": s1["domainsAvailable"], "H1": raw["H1"]["x"], "A1": raw["A1"]["x"]})
            c1_dom_hist.append({"t": t, **s1["domains"]})
            cur_dom.append(s1["domains"])
        regm = {d: (np.mean([x[d] for x in cur_dom if x[d] is not None]) if any(x[d] is not None for x in cur_dom) else None)
                for d in DOMS}
        reg_hist.append((t, regm, L.qs(t + lead)))
    return pd.DataFrame(recs), weights_by_t


# ------------------------------------------------------------------------------------------------ evaluation
def quarter_pairs(y, a, b, seed=2026, n=2000):
    """Paired quarter Brier difference a - b (one row per quarter), bootstrap CI and sign test."""
    d = (a - y) ** 2 - (b - y) ** 2
    rng = np.random.default_rng(seed)
    bs = [float(np.mean(rng.choice(d, len(d), replace=True))) for _ in range(n)]
    w, l_ = int((d < 0).sum()), int((d > 0).sum())
    return {"mean_brier_diff": float(d.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "wins": w, "losses": l_, "sign_p": float(binomtest(w, w + l_, 0.5).pvalue) if w + l_ else 1.0}


def regional_eval(R, lead, out_h, hun63):
    g = R[(R["lead"] == lead) & R["target"].isin(out_h)]
    Q = g.groupby(["origin_quarter", "target", "t"]).agg(**{c: (c, "mean") for c in CANDS}, H1=("H1", "first"),
                                                         n_C=("C1", lambda s: s.notna().sum())).reset_index()
    Q["H_obs"] = Q["target"].map(out_h)
    Q["y"] = (Q["H_obs"] > 11.3).astype(int)
    clim = []
    for t in Q["t"]:
        kn = TS._posted(TS.issue_of(int(t)))
        vals = [h > 11.3 for h in kn.values()]
        clim.append(float(np.mean(vals)) if vals else 0.5)
    Q["CLIM"] = clim
    Q["ALWAYS"] = 1.0
    ph = {}
    for (ld, t, code), v in hun63.items():
        if ld == lead:
            ph.setdefault(t, []).append(v)
    Q["LGBM_hunger"] = Q["t"].map(lambda t: float(np.mean(ph[t])) if t in ph else np.nan)
    common = Q.dropna(subset=CANDS)
    res = {"quarters_all": int(len(Q)), "quarters_common": int(len(common)), "candidates": {}, "baselines": {}}
    for c in CANDS + ["H1", "CLIM", "ALWAYS", "LGBM_hunger"]:
        gg = common.dropna(subset=[c])
        if gg.empty:
            continue
        m = FE.metrics(gg["y"], gg[c])
        m["spearman_with_hunger_level"] = (float(spearmanr(gg[c], gg["H_obs"]).correlation)
                                           if gg[c].nunique() > 1 else None)
        m["quarters"] = int(len(gg))
        (res["candidates"] if c in CANDS else res["baselines"])[c] = m
    pairs = {}
    for c in CANDS:
        for b in ("H1", "CLIM", "ALWAYS", "C0"):
            if c == b:
                continue
            gg = common.dropna(subset=[c, b])
            pairs[f"{c}_vs_{b}"] = quarter_pairs(gg["y"].to_numpy(float), gg[c].to_numpy(float), gg[b].to_numpy(float))
    res["paired"] = pairs
    # R-prov: each province's class against the regional outcome (quarter-clustered)
    gp = g.merge(common[["target", "y"]], on="target")
    res["province_rows"] = {c: {"rows": int(gp[c].notna().sum()),
                                "accuracy": float(((gp[c] >= .5).astype(int) == gp["y"])[gp[c].notna()].mean()),
                                "share_HIGH": float((gp[c] >= .5)[gp[c].notna()].mean())} for c in CANDS}
    return res, Q


def eligibility(R):
    g = R[(R["lead"] == 2) & (R["t"] <= L.qi(LEAD_ORIGINS[2][1]))]
    out = {}
    for c in CANDS:
        comp = float(g.groupby("t")[c].apply(lambda s: s.notna().all()).mean())
        share_high = float((g[c] >= .5)[g[c].notna()].mean())
        sat = {}
        if c != "C0":
            for k in FI.CONTINUOUS:
                s = g[f"C1_ind_{k}"].dropna()
                if len(s):
                    sat[k] = float(max((s >= 0.999).mean(), (s <= 0.001).mean()))
        else:                                   # v1 anchored scores (diagnostics D3, the same Lead-2 rows)
            S = pd.read_csv(HERE.parent / "out" / "firi2_diagnostics" / "v1_saturation_lead2.csv").dropna(subset=["share_at_1"])
            sat = {r.indicator: float(max(r.share_at_1, r.share_at_0)) for r in S.itertuples()}
        worst = max(sat.values()) if sat else 0.0
        out[c] = {"computable_share_lead2_quarters": comp, "share_HIGH_lead2_rows": share_high,
                  "max_single_bound_share": worst, "max_single_bound_indicator": max(sat, key=sat.get) if sat else None,
                  "eligible": bool(comp >= 0.9 and worst < 0.9 and 0.1 <= share_high <= 0.9)}
    return out


def select(reg, elig):
    l2 = reg[2]["candidates"]
    l1 = reg[1]["candidates"]
    ok = [c for c in ("C1", "C2", "C3") if elig[c]["eligible"]]
    if not ok:
        return "C0", "no eligible C1-C3 candidate"
    order = {"C1": 0, "C2": 1, "C3": 2}
    best = sorted(ok, key=lambda c: (-l2[c]["accuracy"], l2[c]["brier"], l1[c]["brier"], order[c]))[0]
    if l2[best]["accuracy"] < l2["C0"]["accuracy"]:
        return "C0", f"{best} is below C0 on Lead-2 R accuracy"
    return best, "selection rule section 5"


def t43_agreement(R, lead):
    Y = F.t43_labels(L.load())[["province_code", "quarter", "T43"]].rename(columns={"quarter": "target"})
    S63 = pd.read_csv(FE.E63 / "sealed" / "predictions.csv", dtype={"province_code": str})
    keys = S63[S63["lead"] == lead][["t", "province_code", "E56_p"]]
    g = R[R["lead"] == lead].merge(keys, on=["t", "province_code"]).merge(Y, on=["province_code", "target"])
    g["y"] = g["T43"].astype(int)
    return {c: FE.metrics(g["y"], g[c]) for c in CANDS + ["E56_p"] if g[c].notna().all()}, int(len(g))


def lgbm_checks():
    S57 = pd.read_csv(FE.E57, dtype={"province_code": str})
    S63 = pd.read_csv(FE.E63 / "sealed" / "predictions.csv", dtype={"province_code": str})
    Y = F.t43_labels(L.load())[["province_code", "quarter", "T43"]].rename(columns={"quarter": "target"})
    D = S63[S63["lead"] == 2].merge(Y, on=["province_code", "target"])
    D["y"] = D["T43"].astype(int)
    D = D.sort_values(["t", "province_code"]).reset_index(drop=True)
    p_cal, thr = [], []
    for r in D.itertuples():
        known = D[(D["target"].map(L.qi) <= L.qi(r.origin_quarter) - 1)]          # label quarter known at the issue
        if len(known) >= 15 and known["y"].nunique() == 2:
            pk = known["E56_p"].clip(1e-4, 1 - 1e-4)
            lr = LogisticRegression(C=1e6).fit(np.log(pk / (1 - pk)).to_numpy().reshape(-1, 1), known["y"])
            pr = float(np.clip(r.E56_p, 1e-4, 1 - 1e-4))
            p_cal.append(float(lr.predict_proba([[np.log(pr / (1 - pr))]])[0, 1]))
            best, bv = 0.5, -1
            for c in np.arange(0.05, 0.951, 0.05):
                pred = (known["E56_p"] >= c).astype(int)
                tpr = ((pred == 1) & (known["y"] == 1)).sum() / max(1, (known["y"] == 1).sum())
                tnr = ((pred == 0) & (known["y"] == 0)).sum() / max(1, (known["y"] == 0).sum())
                if (tpr + tnr) / 2 > bv + 1e-12:
                    best, bv = float(c), (tpr + tnr) / 2
            thr.append(best)
        else:
            p_cal.append(float(r.E56_p))
            thr.append(0.5)
    D["L1_p"] = p_cal
    D["L2_thr"] = thr
    chk = D.merge(S57[["t", "province_code", "E56_p"]], on=["t", "province_code"], suffixes=("", "_57"))
    assert len(D) == 50 and len(chk) == 50 and (chk["E56_p"] - chk["E56_p_57"]).abs().max() < 1e-9
    D["HIGH"] = D["y"]
    pr = H.paired(D, "E56_p", "L1_p", "HIGH", seed=2026)          # Brier(L1) - Brier(E56), quarter-cluster
    raw_pred, l2_pred = (D["E56_p"] >= .5).astype(int), (D["E56_p"] >= D["L2_thr"]).astype(int)

    def bal(pred):
        return float(((pred[D.y == 1] == 1).mean() + (pred[D.y == 0] == 0).mean()) / 2)
    return {"L1": {"metrics": FE.metrics(D["y"], D["L1_p"]), "raw": FE.metrics(D["y"], D["E56_p"]),
                   "brier_diff_L1_minus_raw": pr["mean_brier_diff"], "ci95": [pr["ci95_lo"], pr["ci95_hi"]],
                   "sign_p": pr["sign_p"], "passes": bool(pr["ci95_hi"] < 0 and pr["sign_p"] < 0.05)},
            "L2": {"balanced_accuracy_raw": bal(raw_pred), "balanced_accuracy_L2": bal(l2_pred),
                   "accuracy_raw": float((raw_pred == D.y).mean()), "accuracy_L2": float((l2_pred == D.y).mean()),
                   "recall_HIGH_L2": float((l2_pred[D.y == 1] == 1).mean()),
                   "thresholds_used": sorted(set(thr)), "passes": False}}


def main():
    proto = verify()
    d, X, B = E.load()
    base = base_panel(X)
    a1, hun63, _ = a1_sources()
    out_h = outcome_series()
    R, W = [], {}
    for lead in (1, 2, 3):
        r, w = score_lead(base, a1, lead)
        R.append(r)
        W[lead] = w
    R = pd.concat(R, ignore_index=True)
    reg, regq = {}, []
    for lead in (1, 2, 3):
        reg[lead], q = regional_eval(R[R["t"] <= L.qi(LEAD_ORIGINS[lead][1])], lead, out_h, hun63)
        regq.append(q.assign(lead=lead))
    elig = eligibility(R)
    winner, why = select(reg, elig)
    t43 = {lead: t43_agreement(R, lead) for lead in (1, 2, 3)}
    lg = lgbm_checks()
    l2 = reg[2]["candidates"][winner]
    goal = bool(l2["accuracy"] > 0.75 and l2["accuracy"] > reg[2]["baselines"]["ALWAYS"]["accuracy"]
                and l2["accuracy"] > reg[2]["baselines"]["H1"]["accuracy"])
    OUT.mkdir(parents=True, exist_ok=True)
    H.write_csv(R, OUT / "rows.csv")
    H.write_csv(pd.concat(regq, ignore_index=True), OUT / "regional.csv")
    body = {"schema": "aipheed.firi2.evaluation/1", "protocolSha256": proto, "selected": winner, "selectionReason": why,
            "goal75_on_regional_outcome_lead2": goal, "eligibility": elig, "regional": {str(k): v for k, v in reg.items()},
            "t43_agreement": {str(k): {"rows": v[1], "metrics": v[0]} for k, v in t43.items()},
            "lgbm_checks": lg, "weights_lead2": W[2],
            "evidenceStatus": ("development evidence: the 2022-Q2..2026-Q3 regional outcomes were examined before the "
                               "protocol; the outcome is regional (Balance Luzon); T43 is a food-price label and is "
                               "reported as agreement only")}
    (OUT / "evaluation.json").write_bytes(json.dumps(body, indent=1, default=float).encode("utf-8"))
    EVAL.write_bytes(json.dumps(body, indent=1, default=float).encode("utf-8"))
    # served reference: prior values of every origin are recomputed at runtime from these values; weights per origin
    vals = {k: [] for k in FI.CONTINUOUS}
    seen = set()
    for (tt, code), raw in sorted(base.items()):
        for k in FI.CONTINUOUS:
            x = raw[k]["x"]
            if x is None or (k in FI.NATIONAL and (k, tt) in seen):
                continue
            if k in FI.NATIONAL:
                seen.add((k, tt))
            vals[k].append([L.qs(tt), float(x)])
    wsel = {q: (v.get(winner) if winner in ("C2", "C3") else None) for q, v in W[2].items()}
    ref = {"schema": "aipheed.firi2.reference/1", "protocolSha256": proto, "selected": winner, "values": vals,
           "weightsLead2": wsel}
    ref["content_sha256"] = hashlib.sha256(json.dumps(ref, sort_keys=True).encode()).hexdigest()
    REF.write_bytes(json.dumps(ref, indent=1, sort_keys=True).encode("utf-8"))
    # served history (selected, lead 2) and the prospective seal
    g = R[R["lead"] == 2].copy()
    hist = []
    for r in g.itertuples():
        raw = lead_rows({(r.t, r.province_code): base[(r.t, r.province_code)]}, a1, 2, r.origin_quarter, r.origin_quarter)[0][2]
        pv = prior_values(base, r.t)
        res = FI.score(raw, FI.anchors()) if winner == "C0" else FI.score_v2(raw, pv, wsel.get(r.origin_quarter))
        hist.append({"target": r.target, "origin_quarter": r.origin_quarter, "issue_date": r.issue_date,
                     "province_code": r.province_code,
                     "kind": "forecast" if r.t >= L.qi("2026-Q2") else "backtest", "FIRI": res["firi"], "class": res["class"],
                     "domainsAvailable": res["domainsAvailable"], **{f"dom_{k}": v for k, v in res["domains"].items()},
                     "weights_json": json.dumps(res.get("weights")),
                     "indicators_json": json.dumps({k: {"x": v["x"], "score": v["score"], "status": v["status"]}
                                                    for k, v in res["indicators"].items()})})
    HT = pd.DataFrame(hist)
    H.write_csv(HT, HIST)
    S = HT[HT["kind"] == "forecast"][["origin_quarter", "issue_date", "target", "province_code", "FIRI", "class"]].copy()
    S["method"] = winner
    S["protocolSha256"] = proto
    H.write_csv(S, SEAL)
    (SEAL.with_suffix(".sha256")).write_text(hashlib.sha256(SEAL.read_bytes().replace(b"\r\n", b"\n")).hexdigest() + "\n")
    # console
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print("selected", winner, why, "goal75(R, lead2)", goal)
    print(json.dumps(elig, indent=1))
    for lead in (1, 2, 3):
        rr = reg[lead]
        print(f"--- lead {lead}: quarters {rr['quarters_common']} of {rr['quarters_all']}")
        for k, m in {**rr["candidates"], **rr["baselines"]}.items():
            print(f"{k:12s} acc {m['accuracy']:.3f} prec {m['precision_HIGH']} rec {m['recall_HIGH']} recL {m['recall_LOW']} "
                  f"auc {m['auc_roc']} brier {m['brier']:.3f} rho {m.get('spearman_with_hunger_level')} {m['confusion']}")
        for k, v in rr["paired"].items():
            if k.endswith(("_vs_H1", "_vs_ALWAYS", "_vs_C0")):
                print("  ", k, round(v["mean_brier_diff"], 4), [round(x, 4) for x in v["ci95"]], v["wins"], v["losses"], round(v["sign_p"], 3))
        print("  province rows:", rr["province_rows"])
    for lead, (m, n) in t43.items():
        print("T43 agreement lead", lead, n, {c: (round(v["accuracy"], 3), v["auc_roc"]) for c, v in m.items()})
    print(json.dumps(lg, indent=1, default=float)[:3000])
    print(json.dumps({q: v for q, v in W[2].items() if q >= "2024-Q4"}, indent=0, default=float)[:3000])
    print(HT[HT["kind"] == "forecast"][["target", "province_code", "FIRI", "class"]].to_string())


if __name__ == "__main__":
    main()
