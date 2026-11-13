r"""LONG_GAP_CORRECTION_PROTOCOL.md (sha d1b7747e): FINAL live CALABARZON forecasts with the two long-gap corrections, for the
local dashboard preview. Same inputs, engine, seeds and leads as build_final_live.py; each fit predicts the live rows twice:
elapsed time g (FINAL) and s (time since the latest released round). Probabilities: p = 1/2 p(g) + 1/2 p(s), each from
Phi(mu / sd_adj), sd_adj^2 = sd^2 + q * max(0, elapsed - G_max)/4 (q = RSS anchor process noise per year; G_max = longest training gap).
Writes ../out_corrected/ only. Run from C:\Users\admin\aipheed_hcw\backend with AIPHEED_LIVE_ASOF=2026-11-01 PYTHONPATH=. """
import json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

HERE = Path(__file__).resolve().parents[1]
import os
OUT0, OUT = HERE / "out", HERE / os.environ.get("PREVIEW_BUILD_OUT", "out_corrected")
# PREVIEW_CAND: input panel to use (default: the preview copy). 2026-11-13 by-crop harvest refresh uses the rebuilt branch panel.
CAND = Path(os.environ.get("PREVIEW_CAND", str(OUT0 / "cand_panel.parquet")))
LEADS, SEEDS = (1, 2, 3, 4, 5), (168, 1, 2, 3, 4)
RQ = {"NNS2013": 8054, "FNRI2015": 8062, "ENNS2018": 8074, "ENNS2019": 8078, "ENNS2021": 8086}


def _one(lead, seed):
    from app.e147 import features as Fe
    from app.e150 import model as M
    from app.e151 import prov as Pv
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    from app.e163 import model as C
    from app.e164 import auto as A4
    from app.e166 import nested_source as N
    from app.fi5.target import qindex
    from app.hcw import engine as H
    from app.hcw import final_engine as FE
    from app.hcw import serve as SV
    # --- exactly app.hcw.serve._rows, plus the RSS anchor's process noise q
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    issue = qindex("2026-Q4")
    Hn, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, issue, Pv.ROUNDS, "F")
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(SV.CAL)].assign(T=issue + lead, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"])
    te = N.add_sources(Pv.add_inputs(S, M.rows_for(S, five, [lead], "F")), L, Hn, S_P).reset_index(drop=True)
    tr = N.add_sources(Pv.add_inputs(S, P.tr), L, Hn, S_P).reset_index(drop=True)
    AN = A4.anchors(S, P, tr, te)
    cp = pd.read_parquet(CAND)
    new = [c for c in H.ADD if c in cp and c not in tr]
    tr = tr.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    te = te.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    _, _, q = C.rss_rows(C.RCache(S), te)
    rel = [r for r, qq in RQ.items() if qq + 6 <= int(te["i"].iloc[0])]
    s = (te["T"] - max(RQ[r] for r in rel)).astype(te["gap_q"].dtype)
    T = pd.concat([te.assign(variant="g"), te.assign(gap_q=s.values, variant="s")], ignore_index=True)
    AN2 = {a: (AN[a][0], np.tile(np.asarray(AN[a][1]), 2)) for a in H.ANC}
    r = FE.fit_predict(tr, T, AN2, seed)
    contrib, cols = r["model"].contributions(r["te"])
    return {"lead": lead, "seed": seed, "issue": issue, "province": te["province"].tolist(), "variant": T["variant"].tolist(),
            "elapsed": T["gap_q"].astype(float).tolist(), "g": te["gap_q"].astype(float).tolist(), "s": s.astype(float).tolist(),
            "mu": np.asarray(r["mu"]), "half": np.asarray(r["half"]), "p_engine": np.asarray(r["p"]), "cal": r["cal"], "q": float(np.median(q)),
            "gmax": float(tr["gap_q"].max()), "contrib": contrib, "cols": cols, "X": te}


def main():
    from app.e151 import prov as Pv
    from app.fi5.target import qlabel
    from app.hcw import engine as H
    from app.hcw import serve as SV
    OUT.mkdir(exist_ok=True)
    for f in ("cand_panel.parquet", "lead_horizon.json", "thesis_metrics.json"):
        shutil.copy2(CAND if f == "cand_panel.parquet" else OUT0 / f, OUT / f)
    R = Parallel(n_jobs=len(LEADS) * len(SEEDS))(delayed(_one)(l, s) for l in LEADS for s in SEEDS)
    news = set(Pv.NEWS_ALL)
    # 2026-11-13 (owner brief "official model selection", Section 6): the combined farm-output inputs measure harvests, not weather,
    # and the harvest group is the one with out-of-sample support (06_CONTRIBUTOR_GROUP_VALIDATION.md), so they are attributed to the
    # harvest bar instead of Climate. Set PREVIEW_HARVEST_SPLIT=0 for the original attribution. Forecasts are unchanged.
    _HARV = {"c_agri_yoy", "agri_since", "c_agri_pc"} if os.environ.get("PREVIEW_HARVEST_SPLIT", "1") == "1" else set()
    grp_of = lambda c: "rp_agprod" if (c[3:] if c.startswith("mi_") else c) in _HARV else H.group_of(c[3:] if c.startswith("mi_") else c)
    rows, prov, audit = [], [], []
    for lead in LEADS:
        rs = [r for r in R if r["lead"] == lead]
        n5 = len(rs[0]["province"])
        for k, name in enumerate(rs[0]["province"]):
            pg, ps, mus, sds = [], [], [], []
            for r in rs:
                for blk, (jj, store) in enumerate(((k, pg), (k + n5, ps))):
                    mu, sd = r["mu"][jj], r["half"][jj] / 1.645
                    sd_adj = float(np.sqrt(sd ** 2 + r["q"] * max(0.0, r["elapsed"][jj] - r["gmax"]) / 4.0))
                    p = float(norm.cdf(mu / sd_adj)) if r["cal"] == "raw" else float(r["p_engine"][jj])
                    store.append(p); mus.append(mu); sds.append(sd_adj)
            p_mix = 0.5 * (np.mean(pg) + np.mean(ps))
            mu_m, sd_m = float(np.mean(mus)), float(np.max(sds))
            g, s, gmax = rs[0]["g"][k], rs[0]["s"][k], rs[0]["gmax"]
            # contributions: mean over seeds and over the two elapsed-time variants (additive, so the mean is additive)
            gr = {v: 0.0 for v in SV.BARS.values()}; gn = dict(gr); other = pov = change = 0.0
            for r in rs:
                for jj in (k, k + n5):
                    for j, c in enumerate(r["cols"]):
                        grp, v = grp_of(c), r["contrib"][jj][j] / (2 * len(rs))
                        if grp in SV.BARS:
                            gr[SV.BARS[grp]] += v; gn[SV.BARS[grp]] += v if c in news else 0.0
                        elif grp == "poverty":
                            pov += v
                        else:
                            other += v
                    change += float(r["contrib"][jj].sum()) / (2 * len(rs))
            X, tq = rs[0]["X"], qlabel(rs[0]["issue"] + lead)
            flag = bool(g > gmax or s < g)
            o = {"province_code": SV.CODES[name], "province": name, "quarter": tq, "lead": lead, "issue_date": SV._cutoff("2026-Q4"),
                 "probability": round(float(p_mix), 3), "class": "HIGH" if p_mix >= .5 else "LOW", "score_pct": round(float(SV.pct(mu_m)), 1),
                 "range90_low": round(float(SV.pct(mu_m - 1.645 * sd_m)), 1), "range90_high": round(float(SV.pct(mu_m + 1.645 * sd_m)), 1),
                 "config": " || ".join(r["cfg"] if "cfg" in r else "" for r in rs), "baseline_pct": round(float(SV.pct(mu_m - change)), 2), "change_logit": round(change, 6),
                 "shap_other": round(other, 6), "shap_poverty": round(pov, 6), "model": H.MODEL_ID, "low_confidence": flag,
                 "own_survey_gap_q": int(g), "quarters_since_latest_round": int(s)}
            for v in SV.BARS.values():
                o[f"shap_{v}"], o[f"shap_news_{v}"] = round(gr[v], 6), round(gn[v], 6)
            for c in SV.VALUES:
                o[f"val_{c}"] = None if c not in X or pd.isna(X.at[k, c]) else float(X.at[k, c])
            rows.append(o)
            prov.append({"province": name, "lead": lead, "target_quarter": tq, "score_pct": o["score_pct"], "range90_pct": [o["range90_low"], o["range90_high"]],
                         "p_high": o["probability"], "risk_class": o["class"], "config": "", "low_confidence": flag})
            audit.append({"province": name, "lead": lead, "g": g, "s": s, "G_max": gmax, "q_rss": rs[0]["q"], "cal": sorted({r["cal"] for r in rs}),
                          "p_FINAL_uncorrected": round(float(np.mean([r["p_engine"][k] for r in rs])), 4), "p_g_widened": round(float(np.mean(pg)), 4),
                          "p_s": round(float(np.mean(ps)), 4), "p_corrected": round(float(p_mix), 4), "prevalence_pct": o["score_pct"],
                          "range90": [o["range90_low"], o["range90_high"]]})
    old = json.loads((OUT0 / "live.json").read_text())
    doc = {**old, "name": "FINAL (RATE + MIND) with long-gap corrections (ETMIX elapsed time + survey-age uncertainty): LOCAL PREVIEW, untested",
           "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "provinces": prov,
           "correction_protocol_sha256": "d1b7747ea0ee95055b9797ad79b5f0fb1caf4f4b9767671dd6a6b79dacb2eeeb"}
    (OUT / "live.json").write_text(json.dumps(doc, indent=1), newline="\n")
    pd.DataFrame(rows).to_csv(OUT / "dashboard_rows.csv", index=False, lineterminator="\n")
    A = pd.DataFrame(audit)
    A.to_csv(OUT / "correction_audit.csv", index=False)
    print(A.to_string(index=False))


if __name__ == "__main__":
    main()
