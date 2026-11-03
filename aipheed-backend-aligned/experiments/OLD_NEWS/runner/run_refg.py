"""OLD_NEWS (EXPLORATORY, the last attempt): REF + the 15 regional E85 GDELT columns (PLAN.md).

    python run_refg.py features   # E85 features 2015-Q2..2026-Q3 + checks -> ../out/gdelt_features_2015_2026.csv, coverage
    python run_refg.py fit        # REF reproduction + REF+G walk-forward -> ../out/forecasts_refg.csv
    python run_refg.py score      # R1-R7 at Leads 1-2, decision -> ../out/results.json
    python run_refg.py seal       # only if REF+G passes
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
ROOT = EXP.parents[1]
PLAN = HERE / "PLAN.md"
OUT = HERE / "out"
RAW_OLD = ROOT / "backend" / "data" / "gdelt_e85" / "gkg_calabarzon_2015_2020.parquet"
E85_FEAT = EXP / "E85_GDELT_Events" / "runs" / "20261021T101520Z" / "gdelt_features_k1.csv"
for p in ("E85_GDELT_Events/runner", "E41_Lead2_Audit/runner", "IMPROVE_V2/runner"):
    sys.path.insert(0, str(EXP / p))
import e85_features as G  # noqa: E402
import e41_lib as E41  # noqa: E402
import iv2_lib as V  # noqa: E402
import run_iv2 as R  # noqa: E402

H = V.H
IV2_OUT = EXP / "IMPROVE_V2" / "out"
LEADS_FILE = EXP / "IMPROVE_V2_LEADS" / "out" / "forecasts_leads.csv"
REF_COLS = V.cols(False, False)
GCOLS = list(G.G_REGIONAL)
REFG_COLS = REF_COLS[:-1] + GCOLS + REF_COLS[-1:]
FIRST_G, LAST_G = H.qi("2015-Q2"), H.qi("2026-Q3")
TEST_LEADS = (1, 2)
SEAL_ORIGIN = H.qi("2026-Q3")
MIDDLE = (H.qi("2015-Q2"), H.qi("2020-Q4"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_plan() -> str:
    b = PLAN.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN.md changed after it was hashed"
    return h


# ================================================================================================ features
def load_copy(path: Path) -> pd.DataFrame:
    """e85_features.load(), verbatim, reading `path`, WITHOUT its one assertion (ts >= 2021-01-01): PLAN section 3."""
    d = pd.read_parquet(path)
    d["ts"] = pd.to_datetime(d["DATE"].astype(str), format="%Y%m%d%H%M%S") + pd.Timedelta(hours=8)   # UTC -> PHT
    d = d.sort_values("ts").drop_duplicates("DocumentIdentifier", keep="first")
    d["q"] = d["ts"].dt.year * 4 + (d["ts"].dt.month - 1) // 3
    th = d["V2Themes"].fillna("")
    for f, pat in G.FAMILIES.items():
        d[f] = th.str.contains(pat, regex=True).astype(int)
    d["tone"] = pd.to_numeric(d["V2Tone"].fillna("").str.split(",").str[0], errors="coerce")
    d["affected"] = d["V2Counts"].fillna("").map(lambda s: sum(int(n) for _, n in G.SEVERE_COUNTS.findall(s)))
    loc = d["V2Locations"].fillna("")
    for p, pat in G.PROV.items():
        hit = loc.str.contains(pat, regex=True)
        if p == "PH040300000":
            hit &= ~loc.str.contains("Quezon City", regex=False) | loc.str.contains("Quezon Province|Lucena", regex=True)
        d[p] = hit.astype(int)
    return d


def features():
    plan = check_plan()
    chk = json.loads((OUT / "checks_fetch.json").read_text(encoding="utf-8"))
    assert sha(RAW_OLD) == chk["raw_sha256"], "the 2015-2020 raw file changed"
    orig = G.load()
    copy21 = load_copy(G.RAW)
    same_load = bool(orig.reset_index(drop=True).equals(copy21.reset_index(drop=True)))
    assert same_load, "load_copy differs from e85_features.load on the 2021+ file"
    old = load_copy(RAW_OLD)
    d = pd.concat([old, orig]).sort_values("ts").drop_duplicates("DocumentIdentifier", keep="first")
    F = G.features(d, list(range(FIRST_G, LAST_G + 1)), E41.origin)
    reg = F.drop_duplicates("t")[["t"] + GCOLS].sort_values("t").reset_index(drop=True)
    reg.to_csv(OUT / "gdelt_features_2015_2026.csv", index=False)
    e85 = pd.read_csv(E85_FEAT).drop_duplicates("t")[["t"] + GCOLS]
    m = reg.merge(e85, on="t", suffixes=("", "_e85"))
    diffs = {}
    for t in sorted(m["t"]):
        r = m[m["t"] == t].iloc[0]
        a = np.array([r[c] for c in GCOLS], float)
        b = np.array([r[f"{c}_e85"] for c in GCOLS], float)
        same_nan = bool((np.isnan(a) == np.isnan(b)).all())
        dd = float(np.nanmax(np.abs(a - b))) if np.isfinite(a - b).any() else 0.0
        diffs[H.qs(int(t))] = {"max_abs_diff": dd, "nan_equal": same_nan,
                               "cols_differing": [c for c, x, y in zip(GCOLS, a, b)
                                                  if not (np.isnan(x) and np.isnan(y)) and abs(x - y) > 1e-9]}
    req = {q: v for q, v in diffs.items() if H.qi(q) >= H.qi("2021-Q2")}
    eq_ok = all(v["max_abs_diff"] <= 1e-9 and v["nan_equal"] for v in req.values())
    boundary = d[(d["ts"] >= pd.Timestamp("2021-01-01")) & (d["DocumentIdentifier"].isin(old["DocumentIdentifier"]))]
    # coverage (reported only)
    d["Q"] = d["q"].map(H.qs)
    d["year"] = d["ts"].dt.year
    per_q = d.groupby("Q").size()
    shares = d.groupby("year")[list(G.FAMILIES)].mean().round(4)
    cov = {"records_per_quarter": per_q.to_dict(), "family_share_by_year": shares.to_dict("index"),
           "mean_records_2018Q1_2019Q2": float(per_q.loc["2018-Q1":"2019-Q2"].mean()),
           "mean_records_2017_2020_other": float(pd.concat([per_q.loc["2017-Q1":"2017-Q4"], per_q.loc["2019-Q3":"2020-Q4"]]).mean()),
           "origins_with_fewer_than_20_records": [q for q, n in per_q.items() if n < 20 and FIRST_G <= H.qi(q) <= LAST_G]}
    (OUT / "coverage.json").write_text(json.dumps(cov, indent=1, default=str), encoding="utf-8")
    c = json.loads((OUT / "checks_fetch.json").read_text(encoding="utf-8"))
    c.update({"plan_sha256": plan, "load_copy_equals_e85_load_on_2021_file": same_load,
              "old_rows_after_dedupe": int(len(old)), "rows_2021plus": int(len(orig)),
              "old_records_dated_2021_PHT": int((old["ts"] >= pd.Timestamp("2021-01-01")).sum()),
              "combined_rows": int(len(d)), "e85_2021plus_equality": {"required_2021Q2_2026Q3_ok": eq_ok, "by_quarter": diffs},
              "raw_2021_sha256": sha(G.RAW), "e85_features_sha256": sha(E85_FEAT)})
    (OUT / "checks.json").write_text(json.dumps(c, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"load_copy_ok": same_load, "old_rows": len(old), "old_records_dated_2021_PHT":
                      c["old_records_dated_2021_PHT"], "equality_2021Q2+": eq_ok,
                      "differing_quarters": {q: v for q, v in diffs.items() if v["max_abs_diff"] > 1e-9 or not v["nan_equal"]},
                      "records_per_quarter_2015_2020": {q: int(n) for q, n in per_q.items() if q < "2021"}}, indent=1))
    if not eq_ok:
        raise SystemExit("2021+ features differ from E85's stored values: not fitted (PLAN section 3)")


# ================================================================================================ fit
_G: dict = {}


def _init():
    _G["d"] = H.load()
    T = pd.read_csv(IV2_OUT / "table_pooled.csv", dtype={"area": str})
    g = pd.read_csv(OUT / "gdelt_features_2015_2026.csv")
    _G["T"] = T.merge(g, on="t", how="left")
    _G["lab"] = V.area_labels(_G["d"])


def _origin(job) -> pd.DataFrame:
    """OPTION_1 _origin (V.fit_base, pooled=False, no news) at origin t with the given column list, test Leads 1-2."""
    t, name, cols = job
    d, S, lab = _G["d"], _G["T"], _G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"], te["cfg"] = np.nan, False, None
    shap = None
    if H.eligible(trb):
        cfg = H.lgbm_select(tr, cols, mono=False)
        m = H.LGBM(cfg, cols, False).fit(tr)
        te["p"], te["cfg"] = m.predict(te), cfg["id"]
        if m.m is not None:
            shap = V.shap_frame(m.m, te[cols])
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    te["n_train"] = len(tr)
    out = te[["t", "lead", "q", "p", "fallback", "cfg", "n_train", "h_last", "sws_newest_published"]].assign(name=name)
    if shap is not None:
        out = pd.concat([out, shap.add_prefix("shap_").set_index(out.index)], axis=1)
    return out


def fit():
    plan = check_plan()
    c = json.loads((OUT / "checks.json").read_text(encoding="utf-8"))
    assert c["e85_2021plus_equality"]["required_2021Q2_2026Q3_ok"], "feature checks did not pass"
    jobs = [(t, n, cl) for t in V.ORIGINS for n, cl in (("REF_repro", REF_COLS), ("REF+G", REFG_COLS))]
    with Pool(8, initializer=_init) as pool:
        parts = pool.map(_origin, jobs)
    F = pd.concat(parts, ignore_index=True)
    F.to_csv(OUT / "forecasts_refg.csv", index=False)
    old = pd.read_csv(LEADS_FILE)
    old = old[(old["name"] == "REF") & old["lead"].isin(TEST_LEADS)][["t", "lead", "q", "p", "cfg"]]
    new = F[F["name"] == "REF_repro"][["t", "lead", "q", "p", "cfg"]]
    m = old.merge(new, on=["t", "lead"], how="inner", suffixes=("_old", "_new"))
    norm = lambda s: s.astype(str).str.replace(".0", "", regex=False)  # noqa: E731
    cfg_eq = bool(((m["cfg_old"].isna() & m["cfg_new"].isna()) | (norm(m["cfg_old"]) == norm(m["cfg_new"]))).all())
    rep = {"rows_old": int(len(old)), "matched": int(len(m)), "same_q": bool((m["q_old"] == m["q_new"]).all()),
           "max_abs_diff": float((m["p_old"] - m["p_new"]).abs().max()), "cfg_equal": cfg_eq}
    ok = rep["matched"] == rep["rows_old"] and rep["same_q"] and rep["max_abs_diff"] <= 1e-12 and cfg_eq
    c.update({"reproduction_REF": rep, "reproduced": ok, "versions": R.versions(), "plan_sha256": plan})
    (OUT / "checks.json").write_text(json.dumps(c, indent=1, default=str), encoding="utf-8")
    print(json.dumps(rep, indent=1))
    if not ok:
        raise SystemExit("REF is not reproduced by the refit code: REF+G is not scored")


# ================================================================================================ score
def _summ(r: dict) -> dict:
    m = r["metrics"]
    rules = {k.split()[0]: {"pass": v["pass"], "value": v["value"]} for k, v in r["rules"].items()}
    return {"metrics": {x: m.get(x) for x in ("accuracy", "balanced", "precision", "recall", "f1", "auc", "brier",
                                             "TP", "FP", "FN", "TN")},
            "rules": rules, "failed": [x for x, v in rules.items() if not v["pass"]],
            "all_R1_R7": all(v["pass"] for v in rules.values())}


def score():
    plan = check_plan()
    c = json.loads((OUT / "checks.json").read_text(encoding="utf-8"))
    assert c["reproduced"], "REF reproduction failed"
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    L = pd.read_csv(LEADS_FILE)
    L = L[L["lead"].isin(TEST_LEADS)]
    F = pd.read_csv(OUT / "forecasts_refg.csv")
    g2 = F[F["name"] == "REF+G"]
    FF = pd.concat([L, g2[L.columns]], ignore_index=True)
    res = {"plan_sha256": plan, "label": "EXPLORATORY; development evidence; the last attempt; one candidate",
           "models": {}}
    for name in ("REF", "REF+G"):
        res["models"][name] = {}
        for k in TEST_LEADS:
            W = R.frame(FF, k, lab_bl)
            g = W[W[name].notna()]
            x = _summ(H.evaluate(g, name))
            mid = g[(g["q"] >= MIDDLE[0]) & (g["q"] <= MIDDLE[1])]
            x["n_quarters"] = int(g["q"].nunique())
            x["middle_third_accuracy"] = float(((mid[name] >= .5).astype(int) == mid["y"]).mean())
            x["middle_third_correct"] = f"{int(((mid[name] >= .5).astype(int) == mid['y']).sum())}/{len(mid)}"
            if name == "REF+G":
                x["calls_differing_from_REF"] = int(((g["REF+G"] >= .5) != (g["REF"] >= .5)).sum())
                sh = g2[(g2["lead"] == k) & g2["q"].isin(g["q"])]
                sc = [cc for cc in sh.columns if cc.startswith("shap_")]
                tot = sh[sc].abs().sum().sum()
                x["gdelt_shap_share_pct"] = float(100 * sh[[f"shap_{cc}" for cc in GCOLS]].abs().sum().sum() / tot)
            res["models"][name][str(k)] = x
    passed = all(res["models"]["REF+G"][str(k)]["all_R1_R7"] for k in TEST_LEADS)
    res["decision"] = {"passes_L1_and_L2": passed,
                       "reason": "all R1-R7 pass at Leads 1 and 2" if passed else
                       "REF+G does not pass all of R1-R7 at both leads: REF+news stays the main model under the paper's "
                       "75% rule; the attempts to pass R1-R7 on development data are closed"}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for n, Ls in res["models"].items():
        for k, x in Ls.items():
            m = x["metrics"]
            print(f"{n:6s} L{k}: acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {x['failed']} middle {x['middle_third_correct']}"
                  + (f" | calls changed {x['calls_differing_from_REF']} | GDELT SHAP {x['gdelt_shap_share_pct']:.1f}%"
                     if n == "REF+G" else ""))
    print("DECISION:", res["decision"])


def seal():
    check_plan()
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    if not res["decision"]["passes_L1_and_L2"]:
        print("REF+G did not pass: nothing is sealed (PLAN section 4)")
        return
    raise SystemExit("REF+G passed: write the seal with reviewed code before sealing (not expected)")


if __name__ == "__main__":
    {"features": features, "fit": fit, "score": score, "seal": seal}[sys.argv[1]]()
