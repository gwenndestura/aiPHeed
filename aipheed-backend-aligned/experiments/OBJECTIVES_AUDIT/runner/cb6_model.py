"""C-B6 (CB6_PREREGISTRATION.md, hash checked): C-b (NEWS_V2, grid selection on inner folds) + national rice stocks.

    python cb6_model.py fit     # check the C-b replication, then walk-forward C-B6 -> ../out/cb6_fits.csv
    python cb6_model.py score   # metrics, R1-R7, Algorithm 3, 14-test Holm family, acceptance -> ../out/cb6_results.json

The rice stock features ST1/ST2 are ce6_model's (out/ce6_features.csv, stock month <= issue month - 4).
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
PREREG = HERE / "CB6_PREREGISTRATION.md"
STOCKS = EXP / "LEAD2_RELIABILITY_RESEARCH" / "y12_domestic_rice_supply" / "data_acquired" / "tidy_stocks_national.csv"
LAG_MONTHS, REPS, SEED = 4, 5, 2036
ST = ["ST1", "ST2"]
OUT = HERE / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402

PC, N, V, H, R, A = CE.PC, CE.N, CE.V, CE.H, CE.R, CE.A
NAME = "C-B6"
GROUPS = {"market": ["R_food_yoy", "R_head_yoy", "R_food_mom", "R_rice_yoy"] + H.WORLD,
          "climate": ["ONI_last", "ONI_max12", "tc_mean", "R_C3"], "fish_kill": ["R_C4"], "employment": ["E1"],
          "ofw_remittance": ["E2"], "supply": ST}


def check() -> str:
    b = PREREG.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "C-B6 pre-registration changed"
    return h


def _stocks() -> pd.DataFrame:
    return pd.read_csv(STOCKS).set_index("ym")


def st_values(S: pd.DataFrame, t: int) -> tuple[float, float]:
    """ST1, ST2 at origin t from stock months <= issue month - LAG_MONTHS only."""
    iss = H.issue(t)
    m = int(iss[:4]) * 12 + int(iss[5:7]) - 1 - LAG_MONTHS
    if m not in S.index or m - 12 not in S.index:
        return np.nan, np.nan
    a, b = S.loc[m], S.loc[m - 12]
    if not (b["total"] > 0 and a["total"] > 0):
        return np.nan, np.nan
    return float((a["total"] / b["total"] - 1) * 100), float(100 * a["nfa"] / a["total"] - 100 * b["nfa"] / b["total"])


def features():
    pre = check()
    S = _stocks()
    rows = [{"t": t, **dict(zip(ST, st_values(S, t)))} for t in V.ORIGINS]
    F = pd.DataFrame(rows)
    rng = np.random.default_rng(SEED)
    stable = True
    for t in V.ORIGINS:
        iss = H.issue(t)
        m = int(iss[:4]) * 12 + int(iss[5:7]) - 1 - LAG_MONTHS
        for _ in range(REPS):
            P = S.copy()
            fut = P.index > m
            P.loc[fut, ["total", "nfa", "household", "commercial"]] = rng.uniform(1e5, 1e7, (int(fut.sum()), 4))
            x, y = st_values(P, t), tuple(F.loc[F["t"] == t, ST].iloc[0])
            if not all((np.isnan(u) and np.isnan(v)) or u == v for u, v in zip(x, y)):
                stable = False
    F.to_csv(OUT / "ce6_features.csv", index=False)
    chk = {"prereg_sha256": pre, "leakage_unchanged": stable, "non_missing_share": float(F["ST1"].notna().mean()),
           "first_origin": H.qs(int(F.dropna()["t"].min())), "stocks_file_sha256": hashlib.sha256(STOCKS.read_bytes()).hexdigest()}
    (OUT / "ce6_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    print(json.dumps(chk, indent=1))
    if not stable:
        raise SystemExit("C-E6 leakage check failed")


def _init():
    CE._init()
    N._G["T"] = N._G["T"].merge(pd.read_csv(OUT / "ce6_features.csv"), on="t", how="left")


def _origin(job) -> pd.DataFrame:
    """run_news_v2._origin (C-b) line for line, with the given columns; also returns per-input TreeSHAP."""
    t, name, cols = job
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(N.TEST_LEADS)].copy()
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
    out = te[["t", "lead", "q", "p", "fallback", "cfg"]].assign(name=name).reset_index(drop=True)
    sh = (shap.reset_index(drop=True) if shap is not None else pd.DataFrame(0.0, index=out.index, columns=cols))
    return pd.concat([out, sh.add_prefix("shap_")], axis=1)


def fit():
    pre = check()
    with Pool(8, initializer=_init) as pool:
        rep = pd.concat(pool.map(_origin, [(t, "C-b-replica", PC.CB) for t in V.ORIGINS]), ignore_index=True)
        stored = pd.read_csv(N.OUT / "forecasts.csv")
        stored = stored[stored["name"] == "C-b"].set_index(["t", "lead"])["p"]
        dmax = float((rep.set_index(["t", "lead"])["p"] - stored.reindex(rep.set_index(["t", "lead"]).index)).abs().max())
        assert dmax < 1e-9, f"C-b replication differs from the stored C-b forecasts (max {dmax})"
        F = pd.concat(pool.map(_origin, [(t, NAME, PC.CB + ST) for t in V.ORIGINS]), ignore_index=True)
    F.to_csv(OUT / "cb6_fits.csv", index=False)
    print({"C-b_replication_max_abs_diff": dmax})
    print({"prereg_sha256": pre, "rows": len(F), "origins": int(F["t"].nunique())})


def score():
    pre = check()
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    CBF = pd.read_csv(N.OUT / "forecasts.csv")
    CEF = pd.read_csv(OUT / "ce6_fits.csv")
    F = pd.read_csv(OUT / "cb6_fits.csv")
    for c in {c for cs in GROUPS.values() for c in cs}:      # not an input of C-B6 (E1, E2): SHAP is 0
        if f"shap_{c}" not in F:
            F[f"shap_{c}"] = 0.0
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      CBF[CBF["name"] == "C-b"][["name", "t", "lead", "q", "p"]],
                      CEF[CEF["name"] == "C-E6"][["name", "t", "lead", "q", "p"]],
                      F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; 18th historical attempt", "leads": {}, "algorithm3": {}}
    fam = {}
    for k in PC.TEST_LEADS:
        W = R.frame(comp, k, lab_bl)
        Lk = {n: {"accuracy": PC._acc(W.dropna(subset=[n]), n)} for n in ("C-b", "C-E6", NAME)}
        if k <= 2:
            g = W.dropna(subset=["C-b", "C-E6", NAME])
            for n in ("C-b", "C-E6", NAME):
                Lk[n].update(PC._summ(g, n))
                th = [set(x) for x in np.array_split(np.array(sorted(g["q"].unique())), 3)]
                Lk[n]["thirds"] = [PC._acc(g[g["q"].isin(x)], n) for x in th]
            Lk["vs_C-b"] = {**PC._paired(g, NAME, "C-b"), "calls_differing": int(((g[NAME] >= .5) != (g["C-b"] >= .5)).sum())}
            Lk["vs_C-E6"] = PC._paired(g, NAME, "C-E6")
            era = W[W["t"] >= V.NEWS_ERA]
            for b in PC.COMPS:
                fam[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, NAME, b)
            s = F[(F["lead"] == k) & F["q"].isin(g["q"])]
            grp = pd.DataFrame({gname: sum(s[f"shap_{c}"].fillna(0) for c in cs).abs() for gname, cs in GROUPS.items()})
            sh = grp.div(grp.sum(axis=1).replace(0, np.nan), axis=0) * 100
            Lk["five_group_share_pct_mean"] = {c: float(sh[c].mean()) for c in GROUPS}
            Lk["forecasts_with_all_five_above_0.5pct"] = int((sh >= 0.5).all(axis=1).sum())
            Lk["forecasts_with_group_above_0.5pct"] = {c: int((sh[c] >= 0.5).sum()) for c in GROUPS}
            Lk["n_forecasts"] = int(len(sh))
        res["leads"][str(k)] = Lk
    hp = R.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_14"] = [{"lead": k, "comparator": b, **v, "p_holm_14": hp[(k, b)],
                              "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for n in ("C-b", "C-E6", NAME):
        mx = 0
        for k in PC.TEST_LEADS:
            if res["leads"][str(k)][n]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = mx
    Ls = {k: res["leads"][str(k)] for k in (1, 2)}
    g2 = all(Ls[k]["vs_C-b"]["diff"] < 0 and Ls[k]["vs_C-b"]["p_one_sided"] < .10
             and Ls[k][NAME]["metrics"]["accuracy"] >= Ls[k]["C-b"]["metrics"]["accuracy"] for k in (1, 2))
    res["gates"] = {"G1": all(f["significant"] for f in res["holm_family_14"]), "G2": g2,
                    "G3": all(not Ls[k][NAME]["failed"] for k in (1, 2)), "G4": res["algorithm3"][NAME] >= 2,
                    "G5": all(Ls[k][NAME]["rules"]["R7"]["pass"] for k in (1, 2))}
    res["gates"]["adoption_G2_and_G4"] = g2 and res["gates"]["G4"]
    chk = json.loads((OUT / "ce6_checks.json").read_text(encoding="utf-8"))
    res["acceptance"] = {
        "H7_brier_below_C-b_p_lt_0.10_both_leads": all(Ls[k]["vs_C-b"]["diff"] < 0 and Ls[k]["vs_C-b"]["p_one_sided"] < .10 for k in (1, 2)),
        "R1_R7_both_leads": all(not Ls[k][NAME]["failed"] for k in (1, 2)), "MRLT_ge_2": res["algorithm3"][NAME] >= 2,
        "accuracy_ge_0.75_both_leads": all(Ls[k][NAME]["metrics"]["accuracy"] >= .75 for k in (1, 2)),
        "leakage_check": bool(chk["leakage_unchanged"])}
    res["acceptance"]["passes"] = all(res["acceptance"].values())
    res["beats_all_seven_holm"] = all(f["significant"] for f in res["holm_family_14"])
    last = F[(F["t"] == H.qi("2026-Q3")) & F["lead"].isin([1, 2])]
    lg = pd.DataFrame({gname: sum(last[f"shap_{c}"].fillna(0) for c in cs).abs() for gname, cs in GROUPS.items()})
    res["latest_issue_five_group_pct"] = (lg.div(lg.sum(axis=1), axis=0) * 100).round(1).to_dict("records")
    (OUT / "cb6_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for n in ("C-b", "C-E6", NAME):
            m = res["leads"][k][n]["metrics"]
            print(f"L{k} {n:5s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {res['leads'][k][n]['failed']} "
                  f"thirds {[round(x, 3) for x in res['leads'][k][n]['thirds']]}")
        w = res["leads"][k]["vs_C-E6"]
        print(f"   vs C-E6 diff {w['diff']:+.4f} p {w['p_one_sided']:.3f}")
        v = res["leads"][k]["vs_C-b"]
        print(f"   vs C-b diff {v['diff']:+.4f} p {v['p_one_sided']:.3f} calls changed {v['calls_differing']}; "
              f"all five >0.5%: {res['leads'][k]['forecasts_with_all_five_above_0.5pct']} of {res['leads'][k]['n_forecasts']}; "
              f"mean shares { {c: round(x, 1) for c, x in res['leads'][k]['five_group_share_pct_mean'].items()} }")
    print("significant:", sum(f["significant"] for f in res["holm_family_14"]), "of 14; Algorithm 3:", res["algorithm3"])
    print("Gates:", res["gates"])
    print("Acceptance:", res["acceptance"], "beats all seven:", res["beats_all_seven_holm"])
    print("latest issue (2026-10-01) five-group shares:", res["latest_issue_five_group_pct"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
