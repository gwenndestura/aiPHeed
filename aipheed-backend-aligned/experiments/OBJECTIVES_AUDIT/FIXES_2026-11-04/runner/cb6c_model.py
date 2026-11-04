"""C-B6C (PLAN_CB6C.md, hash checked): C-B6 + one CALABARZON-only news shock signal on Balance Luzon rows.

    python cb6c_model.py build   # CAL_SHOCK from FI6-N events -> ../data/cal_shock_quarterly.csv (+ build json)
    python cb6c_model.py fit     # leakage check, C-B6 replication gate, walk-forward C-B6C -> ../out/cb6c_fits.csv
    python cb6c_model.py score   # metrics, R1-R7, Algorithm 3, H9, Holm family with PERSIST-P -> ../out/cb6c_results.json
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
AUD = HERE.parent
EXP = AUD.parent
PLAN = HERE / "PLAN_CB6C.md"
EVENTS = Path(r"C:\Users\admin\aipheed_final\backend\data\fi6\news_archive\events.parquet")
FEATS = HERE / "data" / "fi6n_news_features_quarterly.csv"
FEATS_SHA = "abc0e59c5cc5265ccb0dcec181057632d3f0bb04cc11bd9b526e81cb1ff88d3e"
SIG = HERE / "data" / "cal_shock_quarterly.csv"
OUT = HERE / "out"
SEED, REPS, MIN_HISTORY, RECENT_DAYS = 2036, 5, 8, 42
LOCAL = ["lgu", "province", "region", "body_mention"]
sys.path.insert(0, str(AUD / "runner"))
import cb6_model as CB  # noqa: E402

PC, N, V, H, R, A = CB.PC, CB.N, CB.V, CB.H, CB.R, CB.A
BASE = PC.CB + CB.ST
NAME, REF, COL = "C-B6C", "C-B6", "CAL_SHOCK"


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN_CB6C changed"
    assert hashlib.sha256(FEATS.read_bytes()).hexdigest() == FEATS_SHA, "FI6-N feature file changed"
    return h


def zscore(raw: pd.Series) -> list[float]:
    z = []
    for i in range(len(raw)):
        hist = raw.iloc[:i].dropna()
        if pd.isna(raw.iloc[i]) or len(hist) < MIN_HISTORY:
            z.append(np.nan)
            continue
        sd = hist.std(ddof=1)
        z.append(float((raw.iloc[i] - hist.mean()) / sd) if sd > 0 else 0.0)
    return z


def build():
    pre = check()
    e = pd.read_parquet(EVENTS)
    s = e[e["relevant"] & ~e["excluded"] & ~e["restated_statistic"] & e["geo_level"].isin(LOCAL)
          & (e["direction"] == "increases_risk") & e["evidence"].isin(["ongoing_disruption", "observed_hardship"])]
    s = s.sort_values("published").drop_duplicates("event_id")
    s = s.assign(t=s["quarter"].map(H.qi))
    o = pd.to_datetime(s["t"].map(H.issue))
    assert (s["published"] < o).all(), "an event is published on or after its quarter's issue date"
    s["w"] = np.where(s["published"] >= o - pd.Timedelta(days=RECENT_DAYS), 2.0, 1.0)
    f = pd.read_csv(FEATS).sort_values("quarter").reset_index(drop=True)
    f["t"] = f["quarter"].map(H.qi)
    w = s.groupby("t")["w"].sum()
    den = f["articles_calabarzon"].astype(float)
    f["raw"] = np.where(den > 0, 100 * f["t"].map(w).fillna(0.0) / den.where(den > 0), np.nan)
    f[COL] = zscore(f["raw"])
    f[["quarter", "t", "raw", COL]].to_csv(SIG, index=False, lineterminator="\n")
    info = {"prereg_sha256": pre, "events_parquet_sha256": hashlib.sha256(EVENTS.read_bytes()).hexdigest(),
            "shock_events": int(len(s)), "recent_weighted_events": int((s["w"] == 2).sum()),
            "quarters_with_signal": int(f[COL].notna().sum()), "first_signal_quarter": f.loc[f[COL].notna(), "quarter"].min(),
            "signal_sha256": hashlib.sha256(SIG.read_bytes()).hexdigest()}
    (HERE / "data" / "cal_shock_build.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(info)


def _signal() -> pd.DataFrame:
    return pd.read_csv(SIG)[["t", "raw", COL]]


def leakage_check(S: pd.DataFrame) -> bool:
    rng = np.random.default_rng(SEED)
    base = S.set_index("t")[COL]
    for t in V.ORIGINS:
        if t not in base.index:
            continue
        for _ in range(REPS):
            r = S["raw"].copy()
            fut = (S["t"] > t).to_numpy()
            r[fut] = rng.uniform(0, 10, int(fut.sum()))
            z = pd.Series(zscore(r), index=S["t"]).loc[t]
            a = base.loc[t]
            if not ((np.isnan(z) and np.isnan(a)) or abs(z - a) < 1e-12):
                return False
    return True


def _init():
    CB._init()
    T = N._G["T"].merge(_signal()[["t", COL]], on="t", how="left")
    T.loc[T["area"] != "BL", COL] = np.nan
    N._G["T"] = T


def fit():
    pre = check()
    S = _signal()
    ok = leakage_check(S)
    ev = S[S["t"].isin(V.ORIGINS)]
    chk = {"prereg_sha256": pre, "signal_leakage_unchanged": ok, "origins_with_signal": int(ev[COL].notna().sum()),
           "first_origin_with_signal": H.qs(int(ev.loc[ev[COL].notna(), "t"].min()))}
    OUT.mkdir(parents=True, exist_ok=True)
    print(chk, flush=True)
    if not ok:
        raise SystemExit("leakage check failed")
    with Pool(8, initializer=_init) as pool:
        rep = pd.concat(pool.map(CB._origin, [(t, "C-B6-replica", BASE) for t in V.ORIGINS]), ignore_index=True)
        st = pd.read_csv(AUD / "out" / "cb6_fits.csv").set_index(["t", "lead"])["p"]
        r = rep.set_index(["t", "lead"])["p"]
        chk["C-B6_replication_max_abs_diff"] = float((r - st.reindex(r.index)).abs().max())
        (OUT / "cb6c_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
        print(chk, flush=True)
        assert chk["C-B6_replication_max_abs_diff"] < 1e-9, "C-B6 replication differs"
        F = pd.concat(pool.map(CB._origin, [(t, NAME, BASE + [COL]) for t in V.ORIGINS]), ignore_index=True)
    F.to_csv(OUT / "cb6c_fits.csv", index=False)
    print({"rows": len(F), "origins": int(F["t"].nunique())})


def score():
    pre = check()
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    PP = pd.read_csv(OUT / "persist_p_forecasts.csv")
    B6 = pd.read_csv(AUD / "out" / "cb6_fits.csv")
    F = pd.read_csv(OUT / "cb6c_fits.csv")
    S = _signal()
    sig_t = set(S.loc[S[COL].notna(), "t"])
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]], L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      PP[["name", "t", "lead", "q", "p"]], B6[["name", "t", "lead", "q", "p"]],
                      F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; attempt 25 on the same 62 quarters", "leads": {},
           "algorithm3": {}}
    fam = {}
    for k in PC.TEST_LEADS:
        W = R.frame(comp, k, lab_bl)
        Lk = {n: {"accuracy": PC._acc(W.dropna(subset=[n]), n)} for n in (REF, NAME)}
        if k <= 2:
            g = W.dropna(subset=[REF, NAME])
            for n in (REF, NAME):
                Lk[n].update(PC._summ(g, n))
                th = [set(x) for x in np.array_split(np.array(sorted(g["q"].unique())), 3)]
                Lk[n]["thirds"] = [PC._acc(g[g["q"].isin(x)], n) for x in th]
            Lk["vs_C-B6"] = {**PC._paired(g, NAME, REF), "calls_differing": int(((g[NAME] >= .5) != (g[REF] >= .5)).sum())}
            ge = g[g["t"].isin(sig_t)]
            Lk["vs_C-B6_signal_era"] = {**PC._paired(ge, NAME, REF), "n_rows": int(len(ge))}
            era = W[W["t"] >= V.NEWS_ERA]
            for b in ["PERSIST-P" if b == "PERSIST" else b for b in PC.COMPS]:
                fam[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, NAME, b)
            s = F[(F["lead"] == k) & F["q"].isin(g["q"])]
            tot = s.filter(like="shap_").abs().sum(axis=1).replace(0, np.nan)
            Lk["signal_shap_share_mean"] = float((s[f"shap_{COL}"].abs() / tot).mean())
        res["leads"][str(k)] = Lk
    hp = R.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_14_persist_p"] = [{"lead": k, "comparator": b, **v, "p_holm_14": hp[(k, b)],
                                        "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for n in (REF, NAME):
        mx = 0
        for k in PC.TEST_LEADS:
            if res["leads"][str(k)][n]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = mx
    L1, L2 = res["leads"]["1"], res["leads"]["2"]
    h9 = L1["vs_C-B6"]["diff"] < 0 and L1["vs_C-B6"]["p_one_sided"] < .05
    rules_ok = all(not res["leads"][k][NAME]["failed"] for k in ("1", "2"))
    res["decision"] = {"H9_lead1_p_lt_0.05": bool(h9),
                       "lead2_secondary_p_lt_0.10": bool(L2["vs_C-B6"]["diff"] < 0 and L2["vs_C-B6"]["p_one_sided"] < .10),
                       "R1_R7_both_leads": bool(rules_ok),
                       "verdict": ("CALABARZON news improves the forecast; C-B6C recommended as main model" if h9 and rules_ok
                                   else "CALABARZON news improves probabilities only; C-B6 stays" if h9
                                   else "CALABARZON news did not improve C-B6; C-B6 stays")}
    (OUT / "cb6c_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for n in (REF, NAME):
            m = res["leads"][k][n]["metrics"]
            print(f"L{k} {n:6s} acc {m['accuracy']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} F1 {m['f1']:.3f} "
                  f"AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {res['leads'][k][n]['failed']} "
                  f"thirds {[round(x, 3) for x in res['leads'][k][n]['thirds']]}")
        v, ve = res["leads"][k]["vs_C-B6"], res["leads"][k]["vs_C-B6_signal_era"]
        print(f"   vs C-B6 diff {v['diff']:+.4f} CI {v['ci95'][0]:+.4f}..{v['ci95'][1]:+.4f} p {v['p_one_sided']:.4f} "
              f"calls changed {v['calls_differing']}; signal era (n={ve['n_rows']}) diff {ve['diff']:+.4f} p {ve['p_one_sided']:.4f}; "
              f"signal SHAP share {res['leads'][k]['signal_shap_share_mean']:.3f}")
    print("Holm family (PERSIST-P): significant", sum(f["significant"] for f in res["holm_family_14_persist_p"]), "of 14")
    for f in res["holm_family_14_persist_p"]:
        if f["comparator"] == "PERSIST-P":
            print(f"   L{f['lead']} vs PERSIST-P diff {f['diff']:+.4f} Holm {f['p_holm_14']:.4f}")
    print("Algorithm 3:", res["algorithm3"])
    print("Decision:", res["decision"])


if __name__ == "__main__":
    {"build": build, "fit": fit, "score": score}[sys.argv[1]]()
