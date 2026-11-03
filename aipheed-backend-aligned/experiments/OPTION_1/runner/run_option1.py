"""OPTION_1: the IMPROVE_V2 "REF+news" walk-forward re-run unchanged, storing forecast leads 1..15.

    python run_option1.py fit     # REF+news (and its PERSIST / CLIM baselines) -> out/forecasts_refnews.csv; reproduction
    python run_option1.py score   # Algorithm 3, Objective 2 metrics, R1-R7, SHAP shares, Objective 4 / H3 (Holm)
    python run_option1.py seal    # the 2027-Q1 Lead-2 forecast -> ../sealed_prospective_REFNEWS.csv + ../SEAL_LEDGER.md

REF+news is IMPROVE_V2's REF arm with the news columns (iv2_lib.cols(pooled=False, news=True)): the same training rows,
eligibility, 8-setting grid, inner chronological selection (hr_lib.lgbm_select), LightGBM settings and seed. No tuning.
IMPROVE_V2 is imported read only; none of its files are written. The only difference from IMPROVE_V2's fit_base is the
list of TEST leads (the training rows already stack leads 1..15), so the fitted models are identical; `fit` checks it.
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
sys.path.insert(0, str(EXP / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402
import run_iv2 as R  # noqa: E402

H = V.H
IV2_OUT = V.OUT                                   # read only
OUT = HERE / "out"
NAME = "REF+news"
COLS = V.cols(False, True)
LEADS = tuple(range(1, H.KMAX + 1))
ACC_MIN, K_ALG3 = 0.75, 8                         # Algorithm 3: k = 1..8, halt at the first failing lead
OBJ4 = ["PERSIST", "PSA-only", "NLP-only", "LOGIT", "ALWAYS-HIGH"]
H3 = ["PERSIST", "NLP-only", "PSA-only", "LOGIT", "LGBM-GOV", "LGBM-NLP"]
SEALED_ON = "2026-11-03"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ================================================================================================ fit
_G = {}


def _init():
    _G["d"] = H.load()
    _G["T"] = pd.read_csv(IV2_OUT / "table_pooled.csv", dtype={"area": str})
    _G["lab"] = V.area_labels(_G["d"])


def _origin(t: int) -> pd.DataFrame:
    """V.fit_base(pooled=False, regression=False, news=True) at origin t, test leads 1..15."""
    d, S, lab = _G["d"], _G["T"], _G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"], te["cfg"] = np.nan, False, None
    shap = None
    if H.eligible(trb):
        cfg = H.lgbm_select(tr, COLS, mono=False)
        m = H.LGBM(cfg, COLS, False).fit(tr)
        te["p"], te["cfg"] = m.predict(te), cfg["id"]
        if m.m is not None:
            shap = V.shap_frame(m.m, te[COLS])
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    te["n_train"] = len(tr)
    if shap is not None:
        te = pd.concat([te, shap.add_prefix("shap_")], axis=1)
    rows = [te.assign(name=NAME)]
    if t >= H.EVAL_FIRST - H.KMAX:                  # baselines as run_iv2.fit (origins extended for leads > 2)
        ps = H.persist_t2(d, t)
        b = te[["t", "lead", "q", "h_last", "sws_newest_published"]]
        rows.append(b.assign(name="PERSIST", p=ps if not np.isnan(ps) else clim, fallback=False))
        rows.append(b.assign(name="CLIM", p=clim, fallback=False))
    return pd.concat(rows, ignore_index=True)


def fit():
    OUT.mkdir(exist_ok=True)
    inputs = {"plan": R.plan_sha(), "hr_data": R.data_hashes(),
              "table_pooled_sha256": sha(IV2_OUT / "table_pooled.csv"),
              "iv2_forecasts_sha256": sha(IV2_OUT / "forecasts.csv"), "iv2_shap_sha256": sha(IV2_OUT / "shap_rows.csv")}
    with Pool(8, initializer=_init) as pool:
        parts = pool.map(_origin, V.ORIGINS)
    F = pd.concat(parts, ignore_index=True)
    shap_cols = [f"shap_{c}" for c in COLS]
    keep = ["name", "t", "lead", "q", "p", "fallback", "cfg", "n_train", "h_last", "sws_newest_published"]
    F[keep].sort_values(["name", "t", "lead"]).to_csv(OUT / "forecasts_refnews.csv", index=False)
    F[F["name"] == NAME][["t", "lead", "q", "fallback"] + shap_cols].sort_values(["t", "lead"]) \
        .to_csv(OUT / "shap_refnews.csv", index=False)
    F = pd.read_csv(OUT / "forecasts_refnews.csv")
    S = pd.read_csv(OUT / "shap_refnews.csv")
    old = pd.read_csv(IV2_OUT / "forecasts.csv")
    rep = {}
    for n in (NAME, "PERSIST", "CLIM"):
        a = old[old["name"] == n][["t", "lead", "q", "p", "cfg"]]
        b = F[(F["name"] == n) & F["lead"].isin([1, 2]) & F["t"].isin(a["t"])][["t", "lead", "q", "p", "cfg"]]
        m = a.merge(b, on=["t", "lead"], how="outer", suffixes=("_iv2", "_new"), indicator=True)
        both = bool(m["_merge"].eq("both").all())
        rep[n] = {"rows_iv2": int(len(a)), "rows_new": int(len(b)), "same_keys": both,
                  "same_target_q": bool((m["q_iv2"] == m["q_new"]).all()),
                  "p_bitwise_equal": bool(both and (m["p_iv2"].to_numpy() == m["p_new"].to_numpy()).all()),
                  "p_max_abs_diff": float((m["p_iv2"] - m["p_new"]).abs().max()),
                  "cfg_equal": bool(both and (m["cfg_iv2"].astype(str) == m["cfg_new"].astype(str)).all())}
    os_ = pd.read_csv(IV2_OUT / "shap_rows.csv")
    os_ = os_[os_["name"] == NAME][["t", "lead"] + shap_cols]
    ns = S[S["lead"].isin([1, 2])][["t", "lead"] + shap_cols]
    ms = os_.merge(ns, on=["t", "lead"], how="outer", suffixes=("_iv2", "_new"), indicator=True)
    dd = max(float(np.nanmax(np.abs(ms[f"{c}_iv2"].to_numpy(float) - ms[f"{c}_new"].to_numpy(float)))
                   if ms[f"{c}_iv2"].notna().any() else 0.0) for c in shap_cols)
    nan_same = all(bool((ms[f"{c}_iv2"].isna() == ms[f"{c}_new"].isna()).all()) for c in shap_cols)
    rep["shap_" + NAME] = {"rows_iv2": int(len(os_)), "same_keys": bool(ms["_merge"].eq("both").all()),
                           "max_abs_diff": dd, "nan_pattern_equal": nan_same}
    ok = (all(v["same_keys"] and v["same_target_q"] and v["p_max_abs_diff"] <= 1e-12 and v["cfg_equal"]
              for k, v in rep.items() if not k.startswith("shap_"))
          and rep["shap_" + NAME]["same_keys"] and rep["shap_" + NAME]["max_abs_diff"] <= 1e-12 and nan_same)
    chk = {"inputs": inputs, "reproduction_leads_1_2": rep, "reproduced": ok, "n_rows": int(len(F)),
           "leads": list(LEADS), "versions": R.versions()}
    (OUT / "checks.json").write_text(json.dumps(chk, indent=1, default=str), encoding="utf-8")
    print(json.dumps(rep, indent=1))
    if not ok:
        raise SystemExit("REF+news Leads 1-2 do NOT reproduce IMPROVE_V2: nothing is scored")
    print("REF+news Leads 1-2 reproduce IMPROVE_V2 exactly (forecasts and SHAP); rows", len(F))


# ================================================================================================ score
def _paired(W, a, b):
    g = W[W[a].notna() & W[b].notna()]
    dv = ((g[a] - g["y"]) ** 2 - (g[b] - g["y"]) ** 2).to_numpy(float)
    return {"n_quarters": int(g["q"].nunique()), "brier_a": float(((g[a] - g["y"]) ** 2).mean()),
            "brier_b": float(((g[b] - g["y"]) ** 2).mean()), "diff": float(dv.mean()),
            "p_one_sided": float(np.mean(H.boot_mean(g["q"].to_numpy(), dv, H.rp()) >= 0)),
            "acc_a": float(((g[a] >= .5).astype(int) == g["y"]).mean()),
            "acc_b": float(((g[b] >= .5).astype(int) == g["y"]).mean())}


def _comparisons(W, era, names):
    out = {c: _paired(era if c in ("NLP-only", "LGBM-NLP") else W, NAME, c) for c in names}
    hp = R.holm({c: v["p_one_sided"] for c, v in out.items()})
    for c in out:
        out[c]["p_holm"] = hp[c]
    return out


def score():
    chk = json.loads((OUT / "checks.json").read_text(encoding="utf-8"))
    assert chk["reproduced"], "reproduction check failed"
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    F = pd.read_csv(OUT / "forecasts_refnews.csv")
    S = pd.read_csv(OUT / "shap_refnews.csv")
    iv2 = pd.read_csv(IV2_OUT / "forecasts.csv")              # stored comparators (Leads 1-2 only)
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["REF", "LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]]])
    res = {"inputs": chk["inputs"], "model": NAME,
           "rule": (f"Algorithm 3: mean fold accuracy >= {ACC_MIN} (one quarter per fold), k = 1..{K_ALG3}, halt at the "
                    "first failing lead"), "leads": {}}
    for k in LEADS:
        f = pd.concat([F[F["lead"] == k], comp[comp["lead"] == k]], ignore_index=True)
        W = R.frame(f, k, lab_bl)
        g = W[W[NAME].notna()]
        full = H.evaluate(g, NAME)
        m = full["metrics"]
        L = {"n_quarters": int(len(g)), "period": f"{H.qs(int(g['q'].min()))}..{H.qs(int(g['q'].max()))}",
             "mean_fold_accuracy": m["accuracy"], "alg3_pass": bool(m["accuracy"] >= ACC_MIN),
             "metrics": {x: m.get(x) for x in ("accuracy", "balanced", "precision", "recall", "f1", "auc", "brier",
                                               "TP", "FP", "FN", "TN")},
             "rules": {x.split()[0]: {"pass": v["pass"], "value": v["value"]} for x, v in full["rules"].items()},
             "failed": [x.split()[0] for x, v in full["rules"].items() if not v["pass"]],
             "persistence_accuracy": float(((g["PERSIST"] >= .5).astype(int) == g["y"]).mean())}
        src = S[(S["lead"] == k) & S["q"].isin(g["q"])].dropna(subset=[f"shap_{COLS[0]}"])
        L["shap"] = {"rows": int(len(src)), "shares": V.group_shares(src, COLS) if len(src) else None}
        if "REF" in W:
            era = W[W["t"] >= V.NEWS_ERA]
            L["objective4"] = _comparisons(W, era, OBJ4)
            L["h3"] = _comparisons(W, era, H3)
            L["vs_REF"] = _paired(W, NAME, "REF")
        res["leads"][f"L{k}"] = L
    mx = 0
    for k in range(1, K_ALG3 + 1):
        if res["leads"][f"L{k}"]["alg3_pass"]:
            mx = k
        else:
            break
    res["max_reliable_lead_alg3"] = mx
    res["first_failing_lead"] = mx + 1
    res["max_reliable_lead_R1_R7"] = next((k - 1 for k in LEADS if res["leads"][f"L{k}"]["failed"]), max(LEADS))
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(f"Maximum Reliable Lead Time (Algorithm 3): {mx}; under R1-R7: {res['max_reliable_lead_R1_R7']}")
    for k in range(1, mx + 2):
        L = res["leads"][f"L{k}"]
        print(k, round(L["mean_fold_accuracy"], 3), "pass" if L["alg3_pass"] else "FAIL", L["failed"],
              "news share", (L["shap"]["shares"] or {}).get("N1 News"))


# ================================================================================================ seal
def seal():
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    F = pd.read_csv(OUT / "forecasts_refnews.csv")
    t, k = V.LAST_ORIGIN, 2
    r = F[(F["name"] == NAME) & (F["t"] == t) & (F["lead"] == k)].iloc[0]
    ps = F[(F["name"] == "PERSIST") & (F["t"] == t) & (F["lead"] == k)].iloc[0]
    d = H.load()
    kn = H.known(d, t, "BL")[-1]
    row = {"issue_date": H.issue(t), "origin": H.qs(t), "lead": k, "target_quarter": H.qs(int(r["q"])), "arm": NAME,
           "p_high": round(float(r["p"]), 6), "class": "HIGH" if r["p"] >= 0.5 else "LOW",
           "persist_p": float(ps["p"]), "newest_sws_published": r["sws_newest_published"],
           "newest_sws_reading": round(float(kn[1]), 2), "threshold": H.H_LINE,
           "target": "SWS Balance Luzon involuntary hunger > 11.3% (quarter mean of non-commissioned rounds)",
           "plan_sha256": res["inputs"]["plan"], "sealed_on": SEALED_ON,
           "label": "SEALED AFTER RESULTS WERE KNOWN (development results examined before sealing)"}
    path = HERE / "sealed_prospective_REFNEWS.csv"
    if path.exists():
        raise SystemExit(f"{path.name} exists: sealed files are never rewritten")
    pd.DataFrame([row]).to_csv(path, index=False)
    h = sha(path)
    (HERE / "SEAL_LEDGER.md").write_text(
        "# OPTION_1 seal ledger (REF+news)\n\n"
        f"Sealed on {SEALED_ON}, **after the walk-forward results of REF+news were known** (IMPROVE_V2 and this "
        "folder's results.json were examined before sealing). It is a prospective forecast: its target quarter has no "
        "published SWS round yet. It is not an independent test of the development results.\n\n"
        "Sealed files are never edited; later forecasts go into new files, each appended below with its SHA-256.\n\n"
        "| File | SHA-256 | Issue date | Lead | Target | P(HIGH) | Sealed on |\n|---|---|---|---|---|---|---|\n"
        f"| `{path.name}` | `{h}` | {row['issue_date']} | {k} | {row['target_quarter']} | {row['p_high']:.6f} | "
        f"{SEALED_ON} |\n", encoding="utf-8")
    print(path.name, h, row["p_high"], row["class"])


if __name__ == "__main__":
    {"fit": fit, "score": score, "seal": seal}[sys.argv[1]]()
