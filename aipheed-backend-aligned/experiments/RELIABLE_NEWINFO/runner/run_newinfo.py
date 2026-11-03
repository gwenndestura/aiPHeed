"""RELIABLE_NEWINFO (EXPLORATORY, the last attempt): exactly two candidates (PLAN.md).

    python run_newinfo.py features  # CHIRPS RF_z3 / RF_z6 per origin -> out/rain_features.csv (+ publication checks)
    python run_newinfo.py fit       # REF reproduction + C2 = REF + rainfall, walk-forward -> out/forecasts_c2.csv
    python run_newinfo.py score     # C1 BLEND and C2: R1-R7 at Leads 1-2, sensitivity, selection -> out/results.json
    python run_newinfo.py seal      # only if a candidate passes -> ../sealed_prospective_NEWINFO.csv + ../SEAL_LEDGER.md

C1 = 0.5 x stored REF + 0.5 x pi_H4L (IMPROVE_V2 table). C2 = IMPROVE_V2 REF (no news) refitted with two rainfall
columns, the IMPROVE_V2 machinery imported read only (the per-origin fit is OPTION_1's _origin with the column list
swapped). R1-R7: hr_lib.evaluate, unedited, at 0.50.
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
PLAN = HERE / "PLAN.md"
OUT = HERE / "out"
DATA = HERE / "data"
sys.path.insert(0, str(EXP / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402
import run_iv2 as R  # noqa: E402

H = V.H
IV2_OUT = EXP / "IMPROVE_V2" / "out"
LEADS_FILE = EXP / "IMPROVE_V2_LEADS" / "out" / "forecasts_leads.csv"
SWS_FILE = EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "data" / "long" / "sws_area_rounds_full.csv"
REF_COLS = V.cols(False, False)
RAIN = ["RF_z3", "RF_z6"]
C2_COLS = REF_COLS[:-1] + RAIN + REF_COLS[-1:]          # rainfall before "lead"; the order changes no tree split rule
TEST_LEADS = (1, 2)
BASE_YEARS = (1981, 1997)
SEAL_ORIGIN = H.qi("2026-Q3")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_plan() -> str:
    b = PLAN.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    assert last.startswith(b"PLAN-SHA256: "), "PLAN.md has no hash line"
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.split()[1].decode() == h, "PLAN.md changed after it was hashed"
    return h


# ================================================================================================ features
def _issue_ym(t: int) -> int:
    o = pd.Timestamp(H.issue(t))
    return o.year * 12 + o.month - 1


def features():
    check_plan()
    M = pd.read_csv(DATA / "chirps_monthly.csv")
    assert M["complete"].all()
    mm = dict(zip(M["ym"].astype(int), M["mm"].astype(float)))

    def total(end: int, n: int) -> float | None:
        v = [mm.get(end - i) for i in range(n)]
        return None if any(x is None for x in v) else float(sum(v))

    def z(end: int, n: int) -> float:
        x = total(end, n)
        if x is None:
            return np.nan
        cal = end % 12
        base = [total(y * 12 + cal, n) for y in range(BASE_YEARS[0], BASE_YEARS[1] + 1)]
        base = [b for b in base if b is not None]
        return (x - np.mean(base)) / np.std(base, ddof=1)

    rows = []
    for t in sorted(set(V.ORIGINS)):
        newest = _issue_ym(t) - 2                       # month m usable only if O(t) >= first day of month m+2
        assert newest + 2 <= _issue_ym(t)
        rows.append({"t": t, "origin": H.qs(t), "issue_date": H.issue(t),
                     "newest_month": f"{newest // 12}-{newest % 12 + 1:02d}",
                     "RF_z3": z(newest, 3), "RF_z6": z(newest, 6)})
    F = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    F.to_csv(OUT / "rain_features.csv", index=False)
    last = F[F["t"] == SEAL_ORIGIN].iloc[0]
    ann = M.assign(y=M["ym"] // 12).groupby("y")["mm"].sum()
    print(F.describe().round(3).to_string())
    print("2026-10-01 issue uses months up to", last["newest_month"], "| mean annual total 1981-2025:",
          round(float(ann.loc[1981:2025].mean())), "mm")


# ================================================================================================ fit
_G = {}


def _init():
    _G["d"] = H.load()
    T = pd.read_csv(IV2_OUT / "table_pooled.csv", dtype={"area": str})
    rf = pd.read_csv(OUT / "rain_features.csv")[["t"] + RAIN]
    _G["T"] = T.merge(rf, on="t", how="left")
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
    jobs = [(t, n, c) for t in V.ORIGINS for n, c in (("REF_repro", REF_COLS), ("C2", C2_COLS))]
    with Pool(8, initializer=_init) as pool:
        parts = pool.map(_origin, jobs)
    F = pd.concat(parts, ignore_index=True)
    F.to_csv(OUT / "forecasts_c2.csv", index=False)
    old = pd.read_csv(LEADS_FILE)
    old = old[(old["name"] == "REF") & old["lead"].isin(TEST_LEADS)][["t", "lead", "q", "p", "cfg"]]
    new = F[F["name"] == "REF_repro"][["t", "lead", "q", "p", "cfg"]]
    m = old.merge(new, on=["t", "lead"], how="inner", suffixes=("_old", "_new"))
    cfg_eq = bool(((m["cfg_old"].isna() & m["cfg_new"].isna()) |
                   (m["cfg_old"].astype(str).str.replace(".0", "", regex=False) ==
                    m["cfg_new"].astype(str).str.replace(".0", "", regex=False))).all())
    rep = {"rows_old": int(len(old)), "matched": int(len(m)), "same_q": bool((m["q_old"] == m["q_new"]).all()),
           "max_abs_diff": float((m["p_old"] - m["p_new"]).abs().max()), "cfg_equal": cfg_eq}
    ok = rep["matched"] == rep["rows_old"] and rep["same_q"] and rep["max_abs_diff"] <= 1e-12 and cfg_eq
    chk = {"plan_sha256": plan, "reproduction_REF": rep, "reproduced": ok,
           "inputs": {"table_pooled": sha(IV2_OUT / "table_pooled.csv"), "forecasts_leads": sha(LEADS_FILE),
                      "chirps_monthly": sha(DATA / "chirps_monthly.csv"), "rain_features": sha(OUT / "rain_features.csv"),
                      "sws_rounds": sha(SWS_FILE)},
           "versions": R.versions()}
    (OUT / "checks.json").write_text(json.dumps(chk, indent=1, default=str), encoding="utf-8")
    print(json.dumps(rep, indent=1))
    if not ok:
        raise SystemExit("REF is not reproduced by the refit code: C2 is not scored")


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
    chk = json.loads((OUT / "checks.json").read_text(encoding="utf-8"))
    assert chk["reproduced"], "REF reproduction failed"
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    L = pd.read_csv(LEADS_FILE)
    L = L[L["lead"].isin(TEST_LEADS)]
    T = pd.read_csv(IV2_OUT / "table_pooled.csv", dtype={"area": str})
    T = T[(T["area"] == "BL") & T["lead"].isin(TEST_LEADS)][["t", "lead", "pi_H4L"]]
    ref = L[L["name"] == "REF"].merge(T, on=["t", "lead"], how="left")
    assert ref["pi_H4L"].notna().all()
    blend = ref.assign(name="BLEND", p=0.5 * ref["p"] + 0.5 * ref["pi_H4L"])[L.columns]
    C2 = pd.read_csv(OUT / "forecasts_c2.csv")
    c2 = C2[C2["name"] == "C2"]
    F = pd.concat([L, blend, c2[L.columns]], ignore_index=True)
    s = pd.read_csv(SWS_FILE)
    phone = sorted({H.qi(q) for q in s.loc[s["mode"].astype(str).str.contains("phone", case=False), "quarter"]})
    res = {"plan_sha256": plan, "label": "EXPLORATORY; development evidence; the last attempt; 2 candidates",
           "phone_quarters_excluded_in_sensitivity": [H.qs(q) for q in phone], "candidates": {}}
    for name, key in (("REF", "REF (reference)"), ("BLEND", "C1"), ("C2", "C2")):
        res["candidates"][key] = {"model": name, "leads": {}}
        for k in TEST_LEADS:
            W = R.frame(F, k, lab_bl)
            g = W[W[name].notna()]
            full = _summ(H.evaluate(g, name))
            sens = _summ(H.evaluate(g[~g["q"].isin(phone)], name))
            full["n_quarters"] = int(g["q"].nunique())
            full["sensitivity_without_phone_quarters"] = {"n_quarters": int(g[~g["q"].isin(phone)]["q"].nunique()),
                                                          **sens}
            if name == "C2":
                sh = c2[(c2["lead"] == k) & c2["q"].isin(g["q"])]
                sc = [c for c in sh.columns if c.startswith("shap_")]
                tot = sh[sc].abs().sum().sum()
                full["rain_shap_share_pct"] = float(100 * sh[[f"shap_{c}" for c in RAIN]].abs().sum().sum() / tot)
            res["candidates"][key]["leads"][str(k)] = full
    for key in ("C1", "C2"):
        c = res["candidates"][key]
        c["passes_L1_and_L2"] = bool(c["leads"]["1"]["all_R1_R7"] and c["leads"]["2"]["all_R1_R7"])
        c["mean_brier"] = float(np.mean([c["leads"][k]["metrics"]["brier"] for k in ("1", "2")]))
    passing = [k for k in ("C1", "C2") if res["candidates"][k]["passes_L1_and_L2"]]
    if not passing:
        dec = {"chosen": None, "reason": "no candidate passes all of R1-R7 at both leads: REF+news stays the main "
                                         "model under the paper's 75% rule; the attempts to pass R1-R7 are closed"}
    elif len(passing) == 1:
        dec = {"chosen": passing[0], "reason": f"{passing[0]} is the only candidate passing all of R1-R7 at both leads"}
    else:
        b = {k: res["candidates"][k]["mean_brier"] for k in passing}
        dec = {"chosen": "C1" if b["C1"] <= b["C2"] else "C2", "reason": f"both pass; lower mean Brier (ties to C1): {b}"}
    res["decision"] = dec
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for key, c in res["candidates"].items():
        for k, x in c["leads"].items():
            m = x["metrics"]
            sv = x["sensitivity_without_phone_quarters"]
            print(f"{key:16s} L{k}: acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} "
                  f"R {m['recall']:.3f} F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {x['failed']}"
                  f" | no-phone failed {sv['failed']}" + (f" | rain SHAP {x['rain_shap_share_pct']:.1f}%"
                                                         if "rain_shap_share_pct" in x else ""))
    print("DECISION:", dec)


# ================================================================================================ seal
def seal():
    plan = check_plan()
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    c = res["decision"]["chosen"]
    if c is None:
        print("no candidate passes: nothing is sealed (PLAN section 5)")
        return
    raise SystemExit(f"{c} passed: write the seal by hand-checked code before sealing (not expected)")


if __name__ == "__main__":
    {"features": features, "fit": fit, "score": score, "seal": seal}[sys.argv[1]]()
