"""C-B6N (PLAN_CB6N.md, hash checked): C-B6 + the seven FI6-N archive news features.

    python cb6n_model.py fit     # leakage check, C-B6 replication gate, walk-forward C-B6N -> ../out/cb6n_fits.csv
    python cb6n_model.py score   # metrics, R1-R7, Algorithm 3, H8, Holm family with PERSIST-P -> ../out/cb6n_results.json
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
PLAN = HERE / "PLAN_CB6N.md"
NEWS_FILE = HERE / "data" / "fi6n_news_features_quarterly.csv"
NEWS_SHA = "abc0e59c5cc5265ccb0dcec181057632d3f0bb04cc11bd9b526e81cb1ff88d3e"
OUT = HERE / "out"
SEED, REPS, MIN_HISTORY = 2036, 5, 8
sys.path.insert(0, str(AUD / "runner"))
import cb6_model as CB  # noqa: E402

PC, N, V, H, R, A = CB.PC, CB.N, CB.V, CB.H, CB.R, CB.A
NEWS_MAP = {"na_market": "risk_share_market", "na_climate": "risk_share_climate", "na_employment": "risk_share_employment",
            "na_remittance": "risk_share_remittance", "na_poverty": "risk_share_poverty",
            "na_climate_damage": "climate_damage_log", "na_displaced": "displaced_families_log"}
NEWSA = list(NEWS_MAP)
BASE = PC.CB + CB.ST
NAME, REF = "C-B6N", "C-B6"


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN_CB6N changed"
    assert hashlib.sha256(NEWS_FILE.read_bytes()).hexdigest() == NEWS_SHA, "FI6-N feature file changed"
    return h


def asof_news(f: pd.DataFrame) -> pd.DataFrame:
    """FI6-N news_model.asof_news, line for line: z against earlier quarters only (>= 8 non-missing)."""
    f = f.sort_values("quarter").reset_index(drop=True)
    out = pd.DataFrame({"t": f["quarter"].map(H.qi)})
    for k, c in NEWS_MAP.items():
        x = f[c].astype(float)
        z = []
        for i in range(len(x)):
            hist = x.iloc[:i].dropna()
            if pd.isna(x.iloc[i]) or len(hist) < MIN_HISTORY:
                z.append(np.nan)
                continue
            sd = hist.std(ddof=1)
            z.append(float((x.iloc[i] - hist.mean()) / sd) if sd > 0 else 0.0)
        out[k] = z
    return out


def leakage_check(raw: pd.DataFrame, Z: pd.DataFrame) -> bool:
    rng = np.random.default_rng(SEED)
    qi = raw["quarter"].map(H.qi)
    base = Z.set_index("t")
    for t in V.ORIGINS:
        if t not in base.index:
            continue
        for _ in range(REPS):
            P = raw.copy()
            fut = (qi > t).to_numpy()
            for c in NEWS_MAP.values():
                P.loc[fut, c] = rng.uniform(0, 10, int(fut.sum()))
            z = asof_news(P).set_index("t").loc[t, NEWSA]
            a = base.loc[t, NEWSA]
            if not all((np.isnan(u) and np.isnan(v)) or abs(u - v) < 1e-12 for u, v in zip(z, a)):
                return False
    return True


def _init():
    CB._init()
    Z = asof_news(pd.read_csv(NEWS_FILE))
    N._G["T"] = N._G["T"].merge(Z, on="t", how="left")


def fit():
    pre = check()
    raw = pd.read_csv(NEWS_FILE)
    Z = asof_news(raw)
    ok = leakage_check(raw, Z)
    ev = Z[Z["t"].isin(V.ORIGINS)]
    chk = {"prereg_sha256": pre, "news_leakage_unchanged": ok, "origins": len(V.ORIGINS),
           "origins_with_any_news": int(ev[NEWSA].notna().any(axis=1).sum()),
           "first_origin_with_news": H.qs(int(ev[ev[NEWSA].notna().any(axis=1)]["t"].min()))}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cb6n_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    print(chk, flush=True)
    if not ok:
        raise SystemExit("news leakage check failed")
    with Pool(8, initializer=_init) as pool:
        rep = pd.concat(pool.map(CB._origin, [(t, "C-B6-replica", BASE) for t in V.ORIGINS]), ignore_index=True)
        st = pd.read_csv(AUD / "out" / "cb6_fits.csv").set_index(["t", "lead"])["p"]
        r = rep.set_index(["t", "lead"])["p"]
        dmax = float((r - st.reindex(r.index)).abs().max())
        chk["C-B6_replication_max_abs_diff"] = dmax
        (OUT / "cb6n_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
        print({"C-B6_replication_max_abs_diff": dmax}, flush=True)
        assert dmax < 1e-9, f"C-B6 replication differs ({dmax})"
        F = pd.concat(pool.map(CB._origin, [(t, NAME, BASE + NEWSA) for t in V.ORIGINS]), ignore_index=True)
    F.to_csv(OUT / "cb6n_fits.csv", index=False)
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
    F = pd.read_csv(OUT / "cb6n_fits.csv")
    Z = asof_news(pd.read_csv(NEWS_FILE))
    news_t = set(Z[Z[NEWSA].notna().any(axis=1)]["t"])
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]], L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      PP[["name", "t", "lead", "q", "p"]], B6[["name", "t", "lead", "q", "p"]],
                      F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; attempt 24 on the same 62 quarters", "leads": {},
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
            ge = g[g["t"].isin(news_t)]
            Lk["vs_C-B6_news_era"] = {**PC._paired(ge, NAME, REF), "n_rows": int(len(ge))}
            era = W[W["t"] >= V.NEWS_ERA]
            for b in ["PERSIST-P" if b == "PERSIST" else b for b in PC.COMPS]:
                fam[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, NAME, b)
            s = F[(F["lead"] == k) & F["q"].isin(g["q"])]
            tot = s.filter(like="shap_").abs().sum(axis=1).replace(0, np.nan)
            Lk["news_shap_share_mean"] = float((s[[f"shap_{c}" for c in NEWSA]].abs().sum(axis=1) / tot).mean())
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
    h8 = L1["vs_C-B6"]["diff"] < 0 and L1["vs_C-B6"]["p_one_sided"] < .05
    rules_ok = all(not res["leads"][k][NAME]["failed"] for k in ("1", "2"))
    res["decision"] = {"H8_lead1_p_lt_0.05": bool(h8),
                       "lead2_secondary_p_lt_0.10": bool(L2["vs_C-B6"]["diff"] < 0 and L2["vs_C-B6"]["p_one_sided"] < .10),
                       "R1_R7_both_leads": bool(rules_ok),
                       "verdict": ("news improves the forecast; C-B6N recommended as main model" if h8 and rules_ok else
                                   "news improves probabilities only; C-B6 stays" if h8 else
                                   "archive news did not improve C-B6; C-B6 stays")}
    (OUT / "cb6n_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for n in (REF, NAME):
            m = res["leads"][k][n]["metrics"]
            print(f"L{k} {n:6s} acc {m['accuracy']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} F1 {m['f1']:.3f} "
                  f"AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {res['leads'][k][n]['failed']} "
                  f"thirds {[round(x, 3) for x in res['leads'][k][n]['thirds']]}")
        v, ve = res["leads"][k]["vs_C-B6"], res["leads"][k]["vs_C-B6_news_era"]
        print(f"   vs C-B6 diff {v['diff']:+.4f} CI {v['ci95'][0]:+.4f}..{v['ci95'][1]:+.4f} p {v['p_one_sided']:.4f} "
              f"calls changed {v['calls_differing']}; news era (n={ve['n_rows']}) diff {ve['diff']:+.4f} p {ve['p_one_sided']:.4f}; "
              f"news SHAP share {res['leads'][k]['news_shap_share_mean']:.3f}")
    print("Holm family (PERSIST-P): significant", sum(f["significant"] for f in res["holm_family_14_persist_p"]), "of 14")
    for f in res["holm_family_14_persist_p"]:
        if f["comparator"] == "PERSIST-P":
            print(f"   L{f['lead']} vs PERSIST-P diff {f['diff']:+.4f} Holm {f['p_holm_14']:.4f}")
    print("Algorithm 3:", res["algorithm3"])
    print("Decision:", res["decision"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
