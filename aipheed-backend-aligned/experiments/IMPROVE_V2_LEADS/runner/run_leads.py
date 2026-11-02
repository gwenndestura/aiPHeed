"""IMPROVE_V2_LEADS: the IMPROVE_V2 REF walk-forward re-run unchanged, storing forecast leads 1..15 (not 1..2).

    python run_leads.py fit     # REF, PERSIST, CLIM walk-forward -> out/forecasts_leads.csv; reproduction check
    python run_leads.py score   # Algorithm 3 and R1-R7 per lead -> out/results_leads.json, out/summary_leads.md

Nothing in IMPROVE_V2 is changed: iv2_lib and run_iv2 are imported read-only and IMPROVE_V2/out is only read.
The only difference from IMPROVE_V2's fit_base is the list of TEST leads. The training rows already stack leads 1..15,
so every fitted model (configuration, trees, seed) is identical; the reproduction check verifies it.
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
sys.path.insert(0, str(HERE.parent / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402
import run_iv2 as R  # noqa: E402

H = V.H
IV2_OUT = V.OUT                                   # read only
OUT = HERE / "out"
LEADS = tuple(range(1, H.KMAX + 1))
ACC_MIN = 0.75                                    # Algorithm 3


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ================================================================================================ fit
_G = {}


def _init():
    _G["d"] = H.load()
    _G["T"] = pd.read_csv(IV2_OUT / "table_pooled.csv", dtype={"area": str})
    _G["lab"] = V.area_labels(_G["d"])


def _ref_origin(t: int) -> pd.DataFrame:
    """V.fit_base(pooled=False, regression=False, news=False) at origin t, test leads 1..15. Same training rows, same
    eligibility, same lgbm_select (inner chronological validation over H.GRID), same LGBM and seed."""
    d, S, lab = _G["d"], _G["T"], _G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    cc = V.cols(False, False)
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"], te["cfg"] = np.nan, False, None
    if H.eligible(trb):
        cfg = H.lgbm_select(tr, cc, mono=False)
        m = H.LGBM(cfg, cc, False).fit(tr)
        te["p"], te["cfg"] = m.predict(te), cfg["id"]
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    te["n_train"] = len(tr)
    rows = [te.assign(name="REF")]
    # baselines as in run_iv2.fit. run_iv2 computes them at origins 2009-Q3.. only, which covers leads 1-2; lead k
    # needs origins from EVAL_FIRST - k, so they start at EVAL_FIRST - KMAX here (same definitions, earlier origins)
    if t >= H.EVAL_FIRST - H.KMAX:
        ps = H.persist_t2(d, t)
        b = te[["t", "lead", "q", "h_last", "sws_newest_published"]]
        rows.append(b.assign(name="PERSIST", p=ps if not np.isnan(ps) else clim, fallback=False))
        rows.append(b.assign(name="CLIM", p=clim, fallback=False))
    return pd.concat(rows, ignore_index=True)


def fit():
    OUT.mkdir(exist_ok=True)
    inputs = {"plan": R.plan_sha(), "hr_data": R.data_hashes(),
              "table_pooled_sha256": sha(IV2_OUT / "table_pooled.csv"),
              "iv2_forecasts_sha256": sha(IV2_OUT / "forecasts.csv")}
    with Pool(8, initializer=_init) as pool:
        parts = pool.map(_ref_origin, V.ORIGINS)
    F = pd.concat(parts, ignore_index=True)
    keep = ["name", "t", "lead", "q", "p", "fallback", "cfg", "n_train", "h_last", "sws_newest_published"]
    F = F[keep].sort_values(["name", "t", "lead"]).reset_index(drop=True)
    F.to_csv(OUT / "forecasts_leads.csv", index=False)
    F = pd.read_csv(OUT / "forecasts_leads.csv")       # compare what is stored, as IMPROVE_V2's file is
    # reproduction: every stored IMPROVE_V2 forecast of REF, PERSIST, CLIM at leads 1-2 (all origins)
    old = pd.read_csv(IV2_OUT / "forecasts.csv")
    rep = {}
    for n in ("REF", "PERSIST", "CLIM"):
        a = old[old["name"] == n][["t", "lead", "q", "p", "cfg"]]
        b = F[(F["name"] == n) & F["lead"].isin([1, 2])][["t", "lead", "q", "p", "cfg"]]
        extra = b[~b["t"].isin(a["t"])]                 # baseline origins before 2009-Q3 (not in IMPROVE_V2)
        b = b[b["t"].isin(a["t"])]
        m = a.merge(b, on=["t", "lead"], how="outer", suffixes=("_iv2", "_new"), indicator=True)
        both = m["_merge"].eq("both").all()
        d = (m["p_iv2"] - m["p_new"]).abs()
        rep[n] = {"rows_iv2": int(len(a)), "rows_new": int(len(b)), "extra_new_origins_rows": int(len(extra)),
                  "same_keys": bool(both),
                  "same_target_q": bool((m["q_iv2"] == m["q_new"]).all()),
                  "p_bitwise_equal": bool(both and (m["p_iv2"].to_numpy() == m["p_new"].to_numpy()).all()),
                  "p_max_abs_diff": float(d.max()),
                  "cfg_equal": bool(both and (m["cfg_iv2"].astype(str) == m["cfg_new"].astype(str)).all())}
    ok = all(v["same_keys"] and v["same_target_q"] and v["p_max_abs_diff"] <= 1e-12 and v["cfg_equal"]
             for v in rep.values())
    chk = {"inputs": inputs, "reproduction_leads_1_2": rep, "reproduced": ok, "n_rows": int(len(F)),
           "leads": list(LEADS), "versions": R.versions()}
    (OUT / "checks_leads.json").write_text(json.dumps(chk, indent=1, default=str))
    print(json.dumps(rep, indent=1))
    if not ok:
        raise SystemExit("Leads 1-2 do NOT reproduce IMPROVE_V2: nothing is scored")
    print("Leads 1-2 reproduce IMPROVE_V2 exactly; forecasts written", len(F))


# ================================================================================================ score
def score():
    chk = json.loads((OUT / "checks_leads.json").read_text())
    assert chk["reproduced"], "reproduction check failed"
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    F = pd.read_csv(OUT / "forecasts_leads.csv")
    res = {"inputs": chk["inputs"], "rule": f"Algorithm 3: mean walk-forward accuracy >= {ACC_MIN}, from Lead 1, "
           "stop at the first failing lead; one fold per origin, so mean fold accuracy = accuracy over target quarters",
           "leads": {}}
    for k in LEADS:
        W = R.frame(F, k, lab_bl)
        assert W["q"].nunique() == len(W)
        full = H.evaluate(W[W["REF"].notna()], "REF")
        m = full["metrics"]
        res["leads"][f"L{k}"] = {
            "n_quarters": int(len(W)), "period": f"{H.qs(int(W['q'].min()))}..{H.qs(int(W['q'].max()))}",
            "accuracy": m["accuracy"], "alg3_pass": bool(m["accuracy"] >= ACC_MIN),
            "persistence_accuracy": float(((W["PERSIST"] >= 0.5).astype(int) == W["y"]).mean()),
            "metrics": m, "rules": full["rules"], "allR1R7": full["allR1R7"],
            "fails": [x.split()[0] for x, v in full["rules"].items() if not v["pass"]]}
        W.to_csv(OUT / f"rows_lead{k}.csv", index=False)
    mx = 0
    for k in LEADS:
        if res["leads"][f"L{k}"]["alg3_pass"]:
            mx = k
        else:
            break
    res["max_reliable_lead_alg3"] = mx
    res["first_failing_lead"] = mx + 1 if mx < max(LEADS) else None
    (OUT / "results_leads.json").write_text(json.dumps(res, indent=1, default=str))
    lines = ["| Lead | Quarters | Accuracy | Alg. 3 (≥ 0.75) | Persistence acc. | Balanced | Brier | AUC | R1–R7 failed |",
             "|---|---|---|---|---|---|---|---|---|"]
    for k in LEADS:
        L = res["leads"][f"L{k}"]
        m = L["metrics"]
        lines.append(f"| {k} | {L['n_quarters']} | {m['accuracy']:.3f} | {'pass' if L['alg3_pass'] else 'FAIL'} | "
                     f"{L['persistence_accuracy']:.3f} | {m['balanced']:.3f} | {m['brier']:.3f} | "
                     f"{m['auc'] if m['auc'] is None else round(m['auc'], 3)} | {', '.join(L['fails']) or 'none'} |")
    r7 = ["", "| Lead | R7 value |", "|---|---|"] + [
        f"| {k} | {res['leads'][f'L{k}']['rules'][[x for x in res['leads'][f'L{k}']['rules'] if x.startswith('R7')][0]]['value']} |"
        for k in LEADS]
    (OUT / "summary_leads.md").write_text(
        f"Maximum Reliable Lead Time (Algorithm 3): {mx}\n\n" + "\n".join(lines + r7) + "\n", encoding="utf-8")
    print(f"max reliable lead (Algorithm 3): {mx}")
    print("\n".join(lines + r7))


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
