"""C-E4 (CE4_PREREGISTRATION.md, hash checked): C-E2 plus the target quarter's season (qsin, qcos).

    python ce4_model.py fit     # walk-forward, stacked leads: mean of 8 settings, mean TreeSHAP -> ../out/ce4_fits.csv
    python ce4_model.py score   # metrics, R1-R7, Algorithm 3, 14-test Holm family, gates, driver coverage -> ../out/ce4_results.json
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
PREREG = HERE / "CE4_PREREGISTRATION.md"
OUT = HERE / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402

PC, N, V, H, R, A = CE.PC, CE.N, CE.V, CE.H, CE.R, CE.A
NAME = "C-E4"
GROUPS = {"market": ["R_food_yoy", "R_head_yoy", "R_food_mom", "R_rice_yoy"] + H.WORLD,
          "climate": ["ONI_last", "ONI_max12", "tc_mean", "R_C3"], "fish_kill": ["R_C4"], "employment": ["E1"],
          "ofw_remittance": ["E2"]}
SEASON = ["qsin", "qcos"]


def check() -> str:
    b = PREREG.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "C-E4 pre-registration changed"
    return h


def _origin(t: int) -> pd.DataFrame:
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"].copy()
    m = (src["q"] % 4) * (2 * np.pi / 4)                # quarter of year of the target quarter (calendar)
    src["qsin"], src["qcos"] = np.round(np.sin(m), 12), np.round(np.cos(m), 12)
    te = src[(src["t"] == t) & src["lead"].isin(PC.TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    return _fit(te, tr, clim)


def _fit(te: pd.DataFrame, tr: pd.DataFrame, clim: float) -> pd.DataFrame:
    cols = CE.CE + SEASON
    trb = tr[tr["area"] == "BL"]
    out = te[["t", "lead", "q"]].reset_index(drop=True).assign(name=NAME, fallback=False)
    if not H.eligible(trb):
        out["p"], out["fallback"] = (float(trb["y"].mean()) if len(trb) else clim), True
        return out
    ps, shs = [], []
    for cfg in H.GRID:
        m = H.LGBM(cfg, cols, False).fit(tr)
        ps.append(np.asarray(m.predict(te), float))
        if m.m is not None:
            shs.append(V.shap_frame(m.m, te[cols]).reset_index(drop=True))
        else:
            shs.append(pd.DataFrame(0.0, index=range(len(te)), columns=cols))
    out["p"] = np.mean(ps, axis=0)
    sh = sum(shs) / len(shs)
    return pd.concat([out, sh.add_prefix("shap_")], axis=1)


def fit():
    pre = check()
    with Pool(8, initializer=CE._init) as pool:
        F = pd.concat(pool.map(_origin, V.ORIGINS), ignore_index=True)
    F.to_csv(OUT / "ce4_fits.csv", index=False)
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
    CEF = pd.read_csv(OUT / "ce2_fits.csv")
    F = pd.read_csv(OUT / "ce4_fits.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      CBF[CBF["name"] == "C-b"][["name", "t", "lead", "q", "p"]],
                      CEF[CEF["name"] == "C-E2"][["name", "t", "lead", "q", "p"]],
                      F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; 18th historical attempt", "leads": {}, "algorithm3": {}}
    fam = {}
    for k in PC.TEST_LEADS:
        W = R.frame(comp, k, lab_bl)
        Lk = {n: {"accuracy": PC._acc(W.dropna(subset=[n]), n)} for n in ("C-b", "C-E2", NAME)}
        if k <= 2:
            g = W.dropna(subset=["C-b", "C-E2", NAME])
            for n in ("C-b", "C-E2", NAME):
                Lk[n].update(PC._summ(g, n))
                th = [set(x) for x in np.array_split(np.array(sorted(g["q"].unique())), 3)]
                Lk[n]["thirds"] = [PC._acc(g[g["q"].isin(x)], n) for x in th]
            Lk["vs_C-b"] = {**PC._paired(g, NAME, "C-b"), "calls_differing": int(((g[NAME] >= .5) != (g["C-b"] >= .5)).sum())}
            Lk["vs_C-E2"] = PC._paired(g, NAME, "C-E2")
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
    for n in ("C-b", "C-E2", NAME):
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
    last = F[(F["t"] == H.qi("2026-Q3")) & F["lead"].isin([1, 2])]
    lg = pd.DataFrame({gname: sum(last[f"shap_{c}"].fillna(0) for c in cs).abs() for gname, cs in GROUPS.items()})
    res["latest_issue_five_group_pct"] = (lg.div(lg.sum(axis=1), axis=0) * 100).round(1).to_dict("records")
    pv = F[F["lead"].isin([1, 2])].pivot_table(index="t", columns="lead", values="p")
    res["origins_lead1_equals_lead2"] = [int(((pv[1] - pv[2]).abs() < 1e-9).sum()), int(len(pv))]
    res["latest_issue_p"] = last[["lead", "q", "p"]].to_dict("records")
    (OUT / "ce4_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for n in ("C-b", "C-E2", NAME):
            m = res["leads"][k][n]["metrics"]
            print(f"L{k} {n:5s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {res['leads'][k][n]['failed']} "
                  f"thirds {[round(x, 3) for x in res['leads'][k][n]['thirds']]}")
        v = res["leads"][k]["vs_C-b"]
        print(f"   vs C-b diff {v['diff']:+.4f} p {v['p_one_sided']:.3f} calls changed {v['calls_differing']}; "
              f"all five >0.5%: {res['leads'][k]['forecasts_with_all_five_above_0.5pct']} of {res['leads'][k]['n_forecasts']}; "
              f"mean shares { {c: round(x, 1) for c, x in res['leads'][k]['five_group_share_pct_mean'].items()} }")
    print("significant:", sum(f["significant"] for f in res["holm_family_14"]), "of 14; Algorithm 3:", res["algorithm3"])
    print("Gates:", res["gates"])
    print("L1=L2 origins:", res["origins_lead1_equals_lead2"], "latest p:", res["latest_issue_p"])
    print("latest issue (2026-10-01) five-group shares:", res["latest_issue_five_group_pct"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
