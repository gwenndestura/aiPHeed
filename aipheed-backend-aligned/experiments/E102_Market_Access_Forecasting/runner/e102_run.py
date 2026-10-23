"""E102 runner (PROTOCOL.md, frozen sha in PROTOCOL_SHA256.txt). Reads only served, local files; writes only ../out/.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E102_Market_Access_Forecasting/runner/e102_run.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
sys.path.insert(0, str(HERE))
import e102_lib as L  # noqa: E402

R, E101, np, pd, TS, qi, qs = L.R, L.E101, L.np, L.pd, L.TS, L.qi, L.qs
from scipy.stats import spearmanr  # noqa: E402

EVAL_END = {1: "2026-Q2", 2: "2026-Q1"}
# E101's row builder, extended (by assignment, documented) to origin 2026-Q3 at Lead 1 for the prospective seal only
E101.LEAD_ORIGINS = {1: ("2021-Q4", "2026-Q3"), 2: ("2021-Q4", "2026-Q1"), 3: ("2021-Q4", "2025-Q4")}
MODEL_COLS = {"M0": ["H_last"], "M1": ["H_last", "A2raw", "A3raw"], "M2": ["H_last", "REL", "PERS"],
              "M3": ["H_last", "REL", "PERS", "E1raw", "RELxE"], "M4": ["REL", "PERS", "E1raw"],
              "M5": ["H_last", "LVL", "REL", "PERS", "ACC", "VOL", "LAG"], "GBM3": ["H_last", "REL", "PERS", "E1raw", "RELxE"]}
GROUPS_M3 = {"hunger": ["H_last"], "price": ["REL", "PERS", "RELxE"], "economic": ["E1raw", "RELxE"]}


def verify():
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((HERE.parent / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert got == want, "PROTOCOL.md changed after freezing"
    E101.verify()
    return got


def mean(v):
    v = [x for x in v if x is not None and not (isinstance(x, float) and np.isnan(x))]
    return float(np.mean(v)) if v else None


def regional_eval(arms: dict, out_h: dict, lead: int, t_from="2021-Q4") -> pd.DataFrame:
    """arms: name -> {target: regional value}. One row per evaluated target quarter."""
    targets = sorted({qs(t + lead) for t in range(qi(t_from), qi(EVAL_END[lead]) + 1) if qs(t + lead) in out_h}, key=qi)
    Q = pd.DataFrame({"target": targets})
    Q["t"] = Q["target"].map(lambda q: qi(q) - lead)
    Q["H_obs"] = Q["target"].map(out_h)
    Q["y"] = (Q["H_obs"] > R.HUNGER_LINE).astype(int)
    prev = Q["y"].shift(1)
    Q["rising"] = ((Q["y"] == 1) & ((prev == 0) | (Q["H_obs"].diff() >= 3))).astype(int)
    for a, v in arms.items():
        Q[a] = Q["target"].map(lambda q: v.get(q, np.nan)).astype(float)
    Q["ALWAYS"] = 1.0
    Q["CLIM"] = [np.mean([h > R.HUNGER_LINE for h in TS._posted(TS.issue_of(int(t))).values()]) or 0.5 for t in Q["t"]]
    return Q


def score_set(Q: pd.DataFrame, names, ref: str, common: list[str]) -> dict:
    g0 = Q.dropna(subset=common)
    res = {"quarters": int(len(g0)), "HIGH": int(g0["y"].sum()), "LOW": int((1 - g0["y"]).sum()),
           "targets": g0["target"].tolist(), "arms": {}}
    for a in names:
        g = g0.dropna(subset=[a])
        if g.empty:
            continue
        m = L.metrics(g["y"], g[a])
        m["quarters"] = int(len(g))
        m["spearman_with_hunger_level"] = float(spearmanr(g[a], g["H_obs"]).correlation) if g[a].nunique() > 1 else None
        if a != ref:
            gg = g.dropna(subset=[ref])
            p = R.paired(gg["y"].to_numpy(float), gg[a].to_numpy(float), gg[ref].to_numpy(float))
            p["class_changes_vs_ref"] = int(((gg[a] >= .5) != (gg[ref] >= .5)).sum())
            m[f"vs_{ref}"] = p
        res["arms"][a] = m
    return res


def main():
    sha = verify()
    OUT.mkdir(exist_ok=True)
    H = R.load_history()
    out_h = R.outcome_series()
    LV = R.level_indicator()
    rel101 = E101.rel_scores(LV)
    S63 = pd.read_csv(E101.E63, dtype={"province_code": str})
    a1_63 = {(int(r.lead), int(r.t), r.province_code): float(r.E56_p_price) for r in S63.itertuples()}
    cpi = L.load_cpi()
    origins = list(range(qi("2021-Q2"), qi("2026-Q3") + 1))
    PNL = L.panel(cpi, origins)
    pct = {k: L.percentiles({key: v[k] for key, v in PNL.items()}) for k in ("REL", "PERS")}
    res = {"protocolSha256": sha, "leads": {}}
    seal = []

    for lead in (1, 2):
        rows = E101.lead_rows(H, lead, a1_63, rel101)
        # ---------------- index arms
        def with_A(fn):
            out = []
            for x in rows:
                y = {**x, "s": dict(x["s"]), "dom": dict(x["dom"])}
                y["s"]["pREL"] = pct["REL"].get((x["t"], x["code"]))
                y["s"]["pPERS"] = pct["PERS"].get((x["t"], x["code"]))
                y["dom"]["A"] = fn(y["s"])
                out.append(y)
            return out
        fb1 = with_A(lambda s: mean([s["A1"], s["A2"], s["A3"], s["pREL"], s["pPERS"]]))
        fb2 = with_A(lambda s: mean([s["A1"], s["pREL"], s["pPERS"]]))
        served, _ = E101.served_equal(rows, lead)
        idx = {"SERVED": served, "FB1": E101.served_equal(fb1, lead)[0], "FB2": E101.served_equal(fb2, lead)[0],
               "FB2-noH": E101.served_equal(fb2, lead, doms=[d for d in R.DOMS if d != "H"])[0]}
        idx["T1"] = {(x["target"], x["code"]): E101.t1_value(x["s"])[0] for x in rows}
        idx["T1-REL"] = {(x["target"], x["code"]): E101.t1_value(x["s"], use_rel=True)[0] for x in rows}

        def t1b(s):
            s2 = dict(s)
            s2["A1"], s2["A2"], s2["A3"] = s["A1"], s.get("pREL"), s.get("pPERS")   # A = mean(A1, pREL, pPERS)
            return E101.t1_value(s2)[0]
        idx["T1-B"] = {(x["target"], x["code"]): t1b(x["s"]) for x in fb2}
        # sensitivity: FB2 with A at a fixed share of the total
        for share in (0.058, 0.10, 1 / 6, 0.25):
            def fixed(rows_, share=share):
                reg_hist, out = [], {}
                for t in sorted({x["t"] for x in rows_}):
                    known = {qs(q): h for q, h in TS._posted(TS.issue_of(t)).items()}
                    w, _, _ = R.evidence_weights([(dm, tq) for (tt, dm, tq) in reg_hist if tt < t], known, list(R.DOMS))
                    cur = [x for x in rows_ if x["t"] == t]
                    for x in cur:
                        dom = x["dom"]
                        av = [d for d in R.DOMS if dom.get(d) is not None]
                        if len(av) < R.MIN_DOMAINS or "A" not in av:
                            out[(x["target"], x["code"])] = None
                            continue
                        ww = {d: (w or {}).get(d, 1.0) if w else 1.0 for d in av if d != "A"}
                        tot = sum(ww.values())
                        out[(x["target"], x["code"])] = share * dom["A"] + (1 - share) * sum(ww[d] / tot * dom[d] for d in ww)
                    reg_hist.append((t, {d: mean([x["dom"][d] for x in cur]) for d in R.DOMS}, qs(t + lead)))
                return out
            idx[f"FB2-A{share:.3f}"] = fixed(fb2)
        # drop-one domain ablation of FB2 (>= 3 domains)
        R.MIN_DOMAINS = 3
        for d in R.DOMS:
            idx[f"FB2-no{d}"] = E101.served_equal(fb2, lead, doms=[x for x in R.DOMS if x != d])[0]
        R.MIN_DOMAINS = 4
        reg_idx = {a: {} for a in idx}
        for a, v in idx.items():
            for q in {x["target"] for x in rows}:
                vals = [v.get((q, p)) for p in R.PROVS]
                vals = [x for x in vals if x is not None]
                if vals:
                    reg_idx[a][q] = float(np.mean(vals))

        # ---------------- regional features for the models
        feats = {}
        for t in sorted({x["t"] for x in rows}):
            cur = [x for x in rows if x["t"] == t]
            rh = TS.regional_hunger(t, lead)
            e1 = mean([next(iter([r["ind"]["E1"]["x"] for _, r in H[(H["t"] == t)].iterrows()]), None)])
            f = {"H_last": rh.get("latestReading"), "H1": rh.get("probabilityAbove11_3"),
                 "A2raw": mean([r["ind"]["A2"]["x"] for _, r in H[H["t"] == t].iterrows()]),
                 "A3raw": mean([r["ind"]["A3"]["x"] for _, r in H[H["t"] == t].iterrows()]), "E1raw": e1}
            for k in L.NEW:
                f[k] = mean([PNL[(t, p)][k] for p in L.PROVS])
            f["RELxE"] = None if f["REL"] is None or f["E1raw"] is None else f["REL"] * f["E1raw"]
            feats[t] = f
        model = {a: {} for a in list(MODEL_COLS) + ["P0"]}
        coefs, shap_m3 = {}, []
        for t, f in feats.items():
            tq = qs(t + lead)
            model["P0"][tq] = f["H1"]
            for a, cols in MODEL_COLS.items():
                tr = L.training_pairs(feats, lead, t, cols)
                model[a][tq] = L.fit_predict("gbm" if a == "GBM3" else "logit", tr, f, cols)
        for a in model:
            model[a] = {q: v for q, v in model[a].items() if v is not None}
        # ablation of M3 by feature group
        for g, drop in GROUPS_M3.items():
            cols = [c for c in MODEL_COLS["M3"] if c not in drop]
            model[f"M3-no-{g}"] = {}
            for t, f in feats.items():
                v = L.fit_predict("logit", L.training_pairs(feats, lead, t, cols), f, cols)
                if v is not None:
                    model[f"M3-no-{g}"][qs(t + lead)] = v
        # production model (as served), regional mean of the sealed E56 scores
        for col, name in (("E56_p", "PROD"), ("E56_p_hunger", "PROD-hunger")):
            g = S63[S63["lead"] == lead].groupby("target")[col].mean().to_dict()
            model[name] = {q: float(v) for q, v in g.items()}

        Q = regional_eval({**reg_idx, **model}, out_h, lead)
        Q.to_csv(OUT / f"regional_lead{lead}.csv", index=False, lineterminator="\n")
        index_names = list(reg_idx)
        model_names = [a for a in model] + ["CLIM", "ALWAYS"]
        core_models = ["P0"] + list(MODEL_COLS)
        rep = {"index_set": score_set(Q, index_names + ["ALWAYS", "CLIM", "P0", "PROD", "PROD-hunger"], "SERVED", ["SERVED"]),
               "model_set": score_set(Q, model_names + ["SERVED", "FB2", "T1-B"], "P0", core_models)}
        # descriptive correlations of the new indicators with the hunger level at t + lead
        desc = {}
        for k in list(L.NEW) + ["RELxE", "A2raw", "A3raw", "E1raw", "H_last"]:
            xs = [(feats[t][k], out_h[qs(t + lead)]) for t in feats if feats[t][k] is not None and qs(t + lead) in out_h
                  and t <= qi(EVAL_END[lead])]
            desc[k] = {"rho": float(spearmanr([a for a, _ in xs], [b for _, b in xs]).correlation), "n": len(xs)} if len(xs) > 4 else None
        rep["descriptive_rho"] = desc
        rep["features"] = {qs(t): f for t, f in feats.items()}
        res["leads"][str(lead)] = rep
        # seal (targets after the data)
        for q in sorted({qs(t + lead) for t in feats}, key=qi):
            if q in ("2026-Q4", "2027-Q1"):
                seal.append({"lead": lead, "target": q, **{a: reg_idx[a].get(q) for a in ("SERVED", "FB1", "FB2", "FB2-noH", "T1-B")},
                             **{a: model[a].get(q) for a in ["P0"] + list(MODEL_COLS)}})

    S = pd.DataFrame(seal)
    blob = S.to_csv(index=False, lineterminator="\n", float_format="%.6f").encode()
    (OUT / "sealed_prospective.csv").write_bytes(blob)
    (OUT / "sealed_prospective.csv.sha256").write_text(hashlib.sha256(blob).hexdigest() + "  sealed_prospective.csv\n")
    res["sealed"] = {"sha256": hashlib.sha256(blob).hexdigest(), "rows": len(S)}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for lead in ("1", "2"):
        for s in ("index_set", "model_set"):
            r = res["leads"][lead][s]
            print("LEAD", lead, s, r["quarters"], "HIGH", r["HIGH"], "LOW", r["LOW"])


if __name__ == "__main__":
    main()
